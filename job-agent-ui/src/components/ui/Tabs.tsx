import { LucideIcon } from 'lucide-react';

export interface Tab {
  id: string;
  label: string;
  icon: LucideIcon;
}

interface TabsProps {
  tabs: Tab[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
}

export function Tabs({ tabs, activeTab, onTabChange }: TabsProps) {
  return (
    <div className="inline-flex flex-wrap gap-1 p-1 rounded-[var(--radius)] bg-[var(--color-border)]/40 border border-[var(--color-border)]">
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`
              inline-flex items-center gap-2 py-2 px-3 rounded-lg text-sm font-medium transition-colors
              ${isActive
                ? 'bg-[var(--color-surface)] text-[var(--color-text)] shadow-[var(--shadow)] border border-[var(--color-border)]'
                : 'text-[var(--color-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface)]/80 border border-transparent'
              }
            `}
          >
            <Icon className="w-4 h-4 shrink-0" />
            <span className="hidden sm:inline">{tab.label}</span>
          </button>
        );
      })}
    </div>
  );
}
