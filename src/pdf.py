"""PDF generation for resumes and cover letters."""

from datetime import datetime
from typing import Any

from fpdf import FPDF

_DARK = (33, 37, 41)
_ACCENT = (33, 37, 41)
_MUTED = (33, 37, 41)
_RULE = (33, 37, 41)

_UNICODE_MAP = {
    "\u2014": "--", "\u2013": "-", "\u2018": "'", "\u2019": "'",
    "\u201c": '"', "\u201d": '"', "\u2022": "-", "\u2026": "...",
    "\u00a0": " ", "\u2010": "-", "\u2011": "-", "\u2012": "-",
    "\u2015": "--", "\u2032": "'", "\u2033": '"', "\u00b7": "-",
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
    MARGIN = 15

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
        self.set_x(self.l_margin)

    @property
    def _w(self):
        return self.w - self.l_margin - self.r_margin


class _ResumePDF(_BasePDF):
    MARGIN = 12.7  # ~0.5 inch margins for tighter layout

    def __init__(self):
        super().__init__(format="letter")
        self.set_auto_page_break(auto=True, margin=self.MARGIN)
        self.set_margins(self.MARGIN, self.MARGIN, self.MARGIN)

    def _section(self, title: str):
        self.ln(1.5)
        self._reset_x()
        self._c(_DARK)
        self.set_font("Helvetica", "B", 10.5)
        self.cell(self._w, 5.5, title.upper(), new_x="LMARGIN", new_y="NEXT")
        self._rule()

    def _two_col(self, left: str, right: str, font_l=("Helvetica", "B", 9.5),
                 font_r=("Helvetica", "", 9)):
        self._reset_x()
        self.set_font(*font_r)
        rw = self.get_string_width(right) + 2
        self.set_font(*font_l)
        self.cell(self._w - rw, 4.8, left)
        self.set_font(*font_r)
        self.cell(rw, 4.8, right, align="R", new_x="LMARGIN", new_y="NEXT")

    def _bullet(self, text: str, indent: float = 4):
        self.set_font("Helvetica", "", 8.5)
        self.set_x(self.l_margin + indent)
        self.multi_cell(self._w - indent, 4, f"-  {text}",
                        new_x="LMARGIN", new_y="NEXT")

    def build(self, contact: dict[str, str], data: dict[str, Any]) -> bytes:
        self.add_page()

        self._c(_DARK)
        self.set_font("Helvetica", "B", 18)
        self._reset_x()
        name = contact.get("name") or "Your Name"
        self.cell(self._w, 8, name, align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(0.5)

        info_parts = []
        for k in ("location", "phone", "email", "linkedin"):
            v = contact.get(k)
            if v:
                info_parts.append(v)
        if "website" in contact and contact["website"]:
            info_parts.append(contact["website"])
        if info_parts:
            self._c(_DARK)
            self.set_font("Helvetica", "", 8)
            self._reset_x()
            self.cell(self._w, 4, "  |  ".join(info_parts),
                      align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

        sections = [
            (self._education, data.get("education", [])),
            (self._skills, data.get("skills", [])),
            (self._experience, data.get("experience", [])),
            (self._projects, data.get("projects", [])),
        ]
        for render, section_data in sections:
            try:
                self._reset_x()
                render(section_data)
            except Exception:
                self._reset_x()

        return bytes(self.output())

    def _education(self, items: list):
        if not items:
            return
        self._section("Education")
        for edu in items:
            self._reset_x()
            if isinstance(edu, dict):
                school = edu.get("school", "")
                year = edu.get("year", "")
                degree = edu.get("degree", "")
                location = edu.get("location", "")

                if school or year:
                    self._two_col(school, year,
                                  font_l=("Helvetica", "B", 9.5),
                                  font_r=("Helvetica", "", 9))
                if degree or location:
                    self._two_col(degree, location,
                                  font_l=("Helvetica", "I", 9),
                                  font_r=("Helvetica", "I", 9))
            else:
                self.set_font("Helvetica", "", 9)
                self.multi_cell(self._w, 4.3, str(edu))
        self.ln(0.5)

    def _skills(self, items: list):
        if not items:
            return
        self._section("Skills")
        self.set_font("Helvetica", "", 8.5)
        for item in items:
            self._reset_x()
            s = str(item)
            if ":" in s:
                cat, rest = s.split(":", 1)
                self.set_font("Helvetica", "B", 8.5)
                cat_w = self.get_string_width(cat + ": ") + 1
                self.cell(cat_w, 4.2, cat + ":")
                self.set_font("Helvetica", "", 8.5)
                self.multi_cell(self._w - cat_w, 4.2, rest.strip(),
                                new_x="LMARGIN", new_y="NEXT")
            else:
                self.multi_cell(self._w, 4.2, f"-  {s}",
                                new_x="LMARGIN", new_y="NEXT")
        self.ln(0.5)

    def _experience(self, items: list):
        if not items:
            return
        self._section("Professional Experience")
        for exp in items:
            if isinstance(exp, dict):
                self._exp_entry(exp)
            else:
                self.set_font("Helvetica", "", 8.5)
                self._reset_x()
                self.multi_cell(self._w, 4, f"-  {exp}")
        self.ln(0.5)

    def _exp_entry(self, exp: dict):
        title = exp.get("title", "")
        company = exp.get("company", "")
        duration = exp.get("duration", "")
        location = exp.get("location", "")

        self._two_col(title, duration,
                      font_l=("Helvetica", "B", 9.5),
                      font_r=("Helvetica", "", 9))
        if company or location:
            self._two_col(company, location,
                          font_l=("Helvetica", "", 9),
                          font_r=("Helvetica", "", 9))

        for bullet in exp.get("bullets", []):
            self._bullet(str(bullet))
        self.ln(1)

    def _projects(self, items: list):
        if not items:
            return
        self._section("Projects")
        for proj in items:
            self._reset_x()
            if isinstance(proj, dict):
                name = proj.get("name", "")
                dates = proj.get("dates", "")
                proj_type = proj.get("type", "")
                location = proj.get("location", "")

                self._two_col(name, dates,
                              font_l=("Helvetica", "B", 9.5),
                              font_r=("Helvetica", "", 9))
                if proj_type or location:
                    self._two_col(proj_type, location,
                                  font_l=("Helvetica", "", 9),
                                  font_r=("Helvetica", "", 9))

                for bullet in proj.get("bullets", []):
                    self._bullet(str(bullet))

                desc = proj.get("description", "")
                if desc and not proj.get("bullets"):
                    self.set_font("Helvetica", "", 8.5)
                    self._reset_x()
                    self.set_x(self.l_margin + 4)
                    self.multi_cell(self._w - 4, 4, desc,
                                    new_x="LMARGIN", new_y="NEXT")
                self.ln(0.5)
            else:
                self.set_font("Helvetica", "", 8.5)
                self.multi_cell(self._w, 4, f"-  {proj}")
        self.ln(0.5)


class _CoverLetterPDF(_BasePDF):
    def __init__(self):
        super().__init__(format="letter")
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(20, 20, 20)

    def build(self, contact: dict[str, str], data: dict[str, Any]) -> bytes:
        self.add_page()
        name = contact.get("name") or "Your Name"

        self._c(_DARK)
        self.set_font("Helvetica", "B", 16)
        self._reset_x()
        self.cell(self._w, 8, name, new_x="LMARGIN", new_y="NEXT")

        parts = [contact.get(k) for k in ("email", "phone", "location") if contact.get(k)]
        if parts:
            self._c(_MUTED)
            self.set_font("Helvetica", "", 9)
            self._reset_x()
            self.cell(self._w, 5, "  |  ".join(parts), new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        self._rule()
        self.ln(4)

        self._c(_DARK)
        self.set_font("Helvetica", "", 10)
        self._reset_x()
        self.cell(self._w, 6, datetime.now().strftime("%B %d, %Y"),
                  new_x="LMARGIN", new_y="NEXT")
        self.ln(6)

        self.set_font("Helvetica", "", 10.5)
        self._reset_x()
        self.cell(self._w, 6, data.get("greeting", "Dear Hiring Manager,"),
                  new_x="LMARGIN", new_y="NEXT")
        self.ln(4)

        paragraphs = data.get("body", data.get("paragraphs", []))
        if isinstance(paragraphs, str):
            paragraphs = [p.strip() for p in paragraphs.split("\n\n") if p.strip()]

        self.set_font("Helvetica", "", 10.5)
        for para in paragraphs:
            self._reset_x()
            self.multi_cell(self._w, 5.5, para)
            self.ln(4)

        self.ln(4)
        self._reset_x()
        self.cell(self._w, 6, data.get("closing", "Sincerely,"),
                  new_x="LMARGIN", new_y="NEXT")
        self.ln(8)
        self.set_font("Helvetica", "B", 10.5)
        self._reset_x()
        self.cell(self._w, 6, name, new_x="LMARGIN", new_y="NEXT")

        return bytes(self.output())


def render_resume(contact: dict[str, str], resume_data: dict[str, Any]) -> bytes:
    return _ResumePDF().build(contact, resume_data)


def render_cover_letter(contact: dict[str, str], cover_data: dict[str, Any]) -> bytes:
    return _CoverLetterPDF().build(contact, cover_data)
