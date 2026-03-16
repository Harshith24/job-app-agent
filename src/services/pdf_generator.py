"""Professional PDF generation for resumes and cover letters."""

from datetime import datetime
from typing import Any, Dict

from fpdf import FPDF

# ── Colour palette ────────────────────────────────────────────
_DARK = (33, 37, 41)
_ACCENT = (30, 64, 175)
_MUTED = (100, 116, 139)
_RULE = (203, 213, 225)


_UNICODE_MAP = {
    "\u2014": "--",  "\u2013": "-",   "\u2018": "'",  "\u2019": "'",
    "\u201c": '"',   "\u201d": '"',   "\u2022": "-",  "\u2026": "...",
    "\u00a0": " ",   "\u2010": "-",   "\u2011": "-",  "\u2012": "-",
    "\u2015": "--",  "\u2032": "'",   "\u2033": '"',  "\u00b7": "-",
}


def _safe(text: str) -> str:
    for src, dst in _UNICODE_MAP.items():
        text = text.replace(src, dst)
    try:
        text.encode("latin-1")
    except UnicodeEncodeError:
        text = text.encode("latin-1", errors="replace").decode("latin-1")
    return text


class _BasePDF(FPDF):
    MARGIN = 15  # mm

    def cell(self, *args, **kwargs):
        args = list(args)
        if len(args) >= 3 and isinstance(args[2], str):
            args[2] = _safe(args[2])
        if "text" in kwargs and isinstance(kwargs["text"], str):
            kwargs["text"] = _safe(kwargs["text"])
        return super().cell(*args, **kwargs)

    def multi_cell(self, *args, **kwargs):
        args = list(args)
        if len(args) >= 3 and isinstance(args[2], str):
            args[2] = _safe(args[2])
        if "text" in kwargs and isinstance(kwargs["text"], str):
            kwargs["text"] = _safe(kwargs["text"])
        return super().multi_cell(*args, **kwargs)

    def _c(self, rgb):
        self.set_text_color(*rgb)

    def _rule(self):
        y = self.get_y()
        self.set_draw_color(*_RULE)
        self.set_line_width(0.3)
        self.line(self.l_margin, y, self.w - self.r_margin, y)
        self.ln(2.5)

    def _reset_x(self):
        """Reset cursor to left margin — call before every block of content."""
        self.set_x(self.l_margin)


# ══════════════════════════════════════════════════════════════
#  Resume PDF
# ══════════════════════════════════════════════════════════════

class _ResumePDF(_BasePDF):

    def __init__(self):
        super().__init__(format="letter")
        self.set_auto_page_break(auto=True, margin=self.MARGIN)
        self.set_margins(self.MARGIN, self.MARGIN, self.MARGIN)

    @property
    def _w(self):
        """Full usable width between margins."""
        return self.w - self.l_margin - self.r_margin

    def _section(self, title: str):
        self.ln(1)
        self._reset_x()
        self._c(_ACCENT)
        self.set_font("Helvetica", "B", 10)
        self.cell(self._w, 6, title.upper(), new_x="LMARGIN", new_y="NEXT")
        self._rule()
        self._c(_DARK)

    def build(self, contact: Dict[str, str], data: Dict[str, Any]) -> bytes:
        self.add_page()

        # ── Name ──
        self._c(_DARK)
        self.set_font("Helvetica", "B", 20)
        self._reset_x()
        self.cell(self._w, 9, contact.get("name") or "Your Name",
                  align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

        # ── Contact line ──
        parts = [contact.get(k) for k in ("email", "phone", "linkedin", "location") if contact.get(k)]
        if parts:
            self._c(_MUTED)
            self.set_font("Helvetica", "", 8.5)
            self._reset_x()
            self.cell(self._w, 4.5, "  |  ".join(parts),
                      align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

        sections = [
            (self._add_summary, data.get("summary", "")),
            (self._add_experience, data.get("experience", [])),
            (self._add_education, data.get("education", [])),
            (self._add_skills, data.get("skills", [])),
            (self._add_projects, data.get("projects", [])),
            (self._add_certifications, data.get("certifications", [])),
        ]
        for fn, section_data in sections:
            try:
                self._reset_x()
                fn(section_data)
            except Exception:
                self._reset_x()

        return bytes(self.output())

    # ── Section renderers ──

    def _add_summary(self, summary: str):
        if not summary:
            return
        self._section("Professional Summary")
        self.set_font("Helvetica", "", 9)
        self._reset_x()
        self.multi_cell(self._w, 4.3, summary)
        self.ln(2)

    def _add_experience(self, items: list):
        if not items:
            return
        self._section("Experience")
        for exp in items:
            if isinstance(exp, dict):
                self._exp_entry(exp)
            else:
                self.set_font("Helvetica", "", 9)
                self._reset_x()
                self.multi_cell(self._w, 4.3, f"-  {exp}")
        self.ln(1)

    def _exp_entry(self, exp: dict):
        title = exp.get("title", "")
        company = exp.get("company", "")
        duration = exp.get("duration", "")
        label = f"{title}  --  {company}" if company else title

        dur_w = 0
        if duration:
            self.set_font("Helvetica", "I", 8)
            dur_w = self.get_string_width(str(duration)) + 4

        self._reset_x()
        self.set_font("Helvetica", "B", 9.5)
        self.cell(self._w - dur_w, 5, label)
        if duration:
            self.set_font("Helvetica", "I", 8)
            self._c(_MUTED)
            self.cell(dur_w, 5, str(duration), align="R",
                      new_x="LMARGIN", new_y="NEXT")
            self._c(_DARK)
        else:
            self.ln()

        indent = 4
        for bullet in exp.get("bullets", []):
            self.set_font("Helvetica", "", 9)
            self.set_x(self.l_margin + indent)
            self.multi_cell(self._w - indent, 4.3, f"-  {bullet}",
                            new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def _add_education(self, items: list):
        if not items:
            return
        self._section("Education")
        for edu in items:
            self._reset_x()
            if isinstance(edu, dict):
                degree = edu.get("degree", "")
                school = edu.get("school", "")
                year = edu.get("year", "")
                label = f"{degree}  --  {school}" if school else degree

                yr_w = 0
                if year:
                    self.set_font("Helvetica", "I", 8)
                    yr_w = self.get_string_width(str(year)) + 4

                self.set_font("Helvetica", "B", 9.5)
                self.cell(self._w - yr_w, 5, label)
                if year:
                    self.set_font("Helvetica", "I", 8)
                    self._c(_MUTED)
                    self.cell(yr_w, 5, str(year), align="R",
                              new_x="LMARGIN", new_y="NEXT")
                    self._c(_DARK)
                else:
                    self.ln()
            else:
                self.set_font("Helvetica", "", 9)
                self.multi_cell(self._w, 4.3, f"-  {edu}")
        self.ln(2)

    def _add_skills(self, items: list):
        if not items:
            return
        self._section("Technical Skills")
        self.set_font("Helvetica", "", 9)
        self._reset_x()
        self.multi_cell(self._w, 4.5, "  |  ".join(items))
        self.ln(2)

    def _add_projects(self, items: list):
        if not items:
            return
        self._section("Projects")
        for proj in items:
            self._reset_x()
            if isinstance(proj, dict):
                self.set_font("Helvetica", "B", 9.5)
                self.cell(self._w, 5, proj.get("name", ""),
                          new_x="LMARGIN", new_y="NEXT")
                desc = proj.get("description", "")
                if desc:
                    self._reset_x()
                    self.set_font("Helvetica", "", 9)
                    self.multi_cell(self._w, 4.3, desc)
                self.ln(1)
            else:
                self.set_font("Helvetica", "", 9)
                self.multi_cell(self._w, 4.3, f"-  {proj}")
        self.ln(1)

    def _add_certifications(self, items: list):
        if not items:
            return
        self._section("Certifications")
        self.set_font("Helvetica", "", 9)
        for cert in items:
            self._reset_x()
            self.multi_cell(self._w, 4.3, f"-  {cert}")
        self.ln(1)


# ══════════════════════════════════════════════════════════════
#  Cover Letter PDF
# ══════════════════════════════════════════════════════════════

class _CoverLetterPDF(_BasePDF):

    def __init__(self):
        super().__init__(format="letter")
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(20, 20, 20)

    @property
    def _w(self):
        return self.w - self.l_margin - self.r_margin

    def build(self, contact: Dict[str, str], data: Dict[str, Any]) -> bytes:
        self.add_page()
        name = contact.get("name") or "Your Name"

        # ── Header ──
        self._c(_DARK)
        self.set_font("Helvetica", "B", 16)
        self._reset_x()
        self.cell(self._w, 8, name, new_x="LMARGIN", new_y="NEXT")

        parts = [contact.get(k) for k in ("email", "phone", "location") if contact.get(k)]
        if parts:
            self._c(_MUTED)
            self.set_font("Helvetica", "", 9)
            self._reset_x()
            self.cell(self._w, 5, "  |  ".join(parts),
                      new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        self._rule()
        self.ln(4)

        # ── Date ──
        self._c(_DARK)
        self.set_font("Helvetica", "", 10)
        self._reset_x()
        self.cell(self._w, 6, datetime.now().strftime("%B %d, %Y"),
                  new_x="LMARGIN", new_y="NEXT")
        self.ln(6)

        # ── Greeting ──
        greeting = data.get("greeting", "Dear Hiring Manager,")
        self.set_font("Helvetica", "", 10.5)
        self._reset_x()
        self.cell(self._w, 6, greeting, new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

        # ── Body paragraphs ──
        paragraphs = data.get("body", data.get("paragraphs", []))
        if isinstance(paragraphs, str):
            paragraphs = [p.strip() for p in paragraphs.split("\n\n") if p.strip()]

        self.set_font("Helvetica", "", 10.5)
        for para in paragraphs:
            self._reset_x()
            self.multi_cell(self._w, 5.5, para)
            self.ln(4)

        # ── Closing ──
        self.ln(4)
        closing = data.get("closing", "Sincerely,")
        self._reset_x()
        self.cell(self._w, 6, closing, new_x="LMARGIN", new_y="NEXT")
        self.ln(8)
        self.set_font("Helvetica", "B", 10.5)
        self._reset_x()
        self.cell(self._w, 6, name, new_x="LMARGIN", new_y="NEXT")

        return bytes(self.output())


# ══════════════════════════════════════════════════════════════
#  Public helpers
# ══════════════════════════════════════════════════════════════

def generate_resume_pdf(contact: Dict[str, str], resume_data: Dict[str, Any]) -> bytes:
    return _ResumePDF().build(contact, resume_data)


def generate_cover_letter_pdf(contact: Dict[str, str], cover_data: Dict[str, Any]) -> bytes:
    return _CoverLetterPDF().build(contact, cover_data)
