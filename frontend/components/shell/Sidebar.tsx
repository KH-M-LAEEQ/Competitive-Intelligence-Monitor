"use client";

import { useState, FormEvent } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useWorkspaceContext } from "@/lib/workspace-context";
import { clearToken } from "@/lib/api";
import {
  GridIcon,
  ListIcon,
  CheckIcon,
  DocIcon,
  CardIcon,
  BookIcon,
  GearIcon,
  PanelCollapseIcon,
  LogoutIcon,
} from "./NavIcons";

const COLLAPSE_STORAGE_KEY = "sidebar-collapsed";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", Icon: GridIcon },
  { href: "/feed", label: "Change Feed", Icon: ListIcon },
  { href: "/approvals", label: "Approval Queue", Icon: CheckIcon, badge: "pending" as const },
  { href: "/briefings", label: "Briefings", Icon: DocIcon },
  { href: "/battlecards", label: "Battlecards", Icon: CardIcon },
  { href: "/response-library", label: "Response Library", Icon: BookIcon },
  { href: "/settings/team", label: "Settings", Icon: GearIcon },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, workspace, workspaces, switchWorkspace, createWorkspace, pendingApprovalsCount } =
    useWorkspaceContext();

  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [collapsed, setCollapsed] = useState(() => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem(COLLAPSE_STORAGE_KEY) === "1";
  });

  function toggleCollapsed() {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem(COLLAPSE_STORAGE_KEY, next ? "1" : "0");
      return next;
    });
  }

  function handleLogout() {
    clearToken();
    router.push("/login");
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!newName.trim()) return;
    await createWorkspace(newName);
    setNewName("");
    setCreating(false);
  }

  const initials = (user?.full_name ?? user?.email ?? "?")
    .trim()
    .split(/\s+/)
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <aside
      className={`sticky top-0 flex h-screen flex-shrink-0 flex-col gap-6 border-r border-[var(--border-subtle)] bg-[var(--bg-sidebar)] py-[22px] transition-[width] duration-200 ${
        collapsed ? "w-[68px] px-2.5" : "w-[244px] px-4"
      }`}
    >
      <div className={`flex items-center ${collapsed ? "flex-col gap-2.5" : "gap-[11px] px-2"}`}>
        <button
          type="button"
          onClick={toggleCollapsed}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className={`flex min-w-0 items-center text-left ${collapsed ? "flex-col gap-2.5" : "flex-1 gap-[11px]"}`}
        >
          <div className="flex h-[30px] w-[30px] flex-shrink-0 items-center justify-center rounded-[9px] bg-[var(--accent)]">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <circle cx="8" cy="8" r="2.4" fill="var(--accent-on)" />
              <path
                d="M8 1.2v2.2M8 12.6v2.2M1.2 8h2.2M12.6 8h2.2"
                stroke="var(--accent-on)"
                strokeWidth="1.5"
                strokeLinecap="round"
              />
              <circle cx="8" cy="8" r="5.6" stroke="var(--accent-on)" strokeWidth="1.2" opacity=".55" />
            </svg>
          </div>
          {!collapsed && (
            <div className="flex min-w-0 flex-1 flex-col gap-0.5">
              <span className="truncate text-[13px] font-semibold tracking-tight">Sentry Signal</span>
              <span className="truncate font-mono text-[9.5px] uppercase tracking-[.13em] text-[var(--text-dim)]">
                CI Monitor v1.0
              </span>
            </div>
          )}
        </button>
        {!collapsed && (
          <button
            type="button"
            onClick={toggleCollapsed}
            title="Collapse sidebar"
            aria-label="Collapse sidebar"
            className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-md text-[var(--text-dim)] hover:bg-[var(--bg-nested)] hover:text-[var(--text-secondary)]"
          >
            <PanelCollapseIcon />
          </button>
        )}
      </div>

      {!collapsed && (
        <div className="flex flex-col gap-1.5 px-1">
          <select
            value={workspace?.id ?? ""}
            onChange={(e) => switchWorkspace(Number(e.target.value))}
            className="w-full rounded-md border border-[var(--border-input)] bg-[var(--bg-input)] px-2 py-1.5 text-xs text-[var(--text-secondary)]"
          >
            {workspaces.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name} ({w.role})
              </option>
            ))}
          </select>
          {creating ? (
            <form onSubmit={handleCreate} className="flex gap-1">
              <input
                autoFocus
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onBlur={() => !newName && setCreating(false)}
                placeholder="Workspace name"
                className="w-full rounded-md border border-[var(--border-input)] bg-[var(--bg-input)] px-2 py-1 text-xs text-[var(--text-secondary)]"
              />
            </form>
          ) : (
            <button
              onClick={() => setCreating(true)}
              className="text-left text-[11px] text-[var(--text-dim)] hover:text-[var(--text-secondary)]"
            >
              + New workspace
            </button>
          )}
        </div>
      )}

      <nav className="flex flex-col gap-[3px]">
        {!collapsed && (
          <div className="px-[10px] pb-2 font-mono text-[9.5px] uppercase tracking-[.14em] text-[var(--text-dimmer)]">
            Workspace
          </div>
        )}
        {NAV_ITEMS.map(({ href, label, Icon, badge }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              title={collapsed ? label : undefined}
              className={`relative flex items-center rounded-[9px] py-[9px] text-[13px] font-medium ${
                collapsed ? "justify-center px-0" : "gap-[11px] px-[10px]"
              }`}
              style={{
                background: active ? "#1A1F26" : "transparent",
                color: active ? "var(--text-primary)" : "var(--text-muted)",
              }}
            >
              <Icon />
              {!collapsed && <span>{label}</span>}
              {badge === "pending" && pendingApprovalsCount > 0 && (
                <span
                  className={
                    collapsed
                      ? "absolute right-[10px] top-[6px] h-[7px] w-[7px] rounded-full bg-[var(--accent)]"
                      : "ml-auto flex h-[18px] min-w-[19px] items-center justify-center rounded-full bg-[var(--accent)] px-1.5 font-mono text-[10px] font-semibold text-[var(--accent-on)]"
                  }
                >
                  {!collapsed && pendingApprovalsCount}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto flex flex-col gap-2.5">
        <div className={`flex items-center px-1.5 py-1 ${collapsed ? "flex-col gap-1.5" : "gap-2.5"}`}>
          <div
            title={user?.full_name ?? user?.email}
            className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-[#242A34] font-mono text-[11px] font-semibold text-[var(--text-secondary)]"
          >
            {initials || "?"}
          </div>
          {collapsed ? (
            <button
              onClick={handleLogout}
              title="Log out"
              aria-label="Log out"
              className="flex h-6 w-6 items-center justify-center rounded-md text-[var(--text-dim)] hover:bg-[var(--bg-nested)] hover:text-[var(--text-secondary)]"
            >
              <LogoutIcon />
            </button>
          ) : (
            <div className="flex min-w-0 flex-col">
              <span className="truncate text-xs font-medium text-[var(--text-primary)]">
                {user?.full_name ?? user?.email}
              </span>
              <button
                onClick={handleLogout}
                className="text-left text-[10.5px] text-[var(--text-dim)] hover:text-[var(--text-secondary)]"
              >
                Log out
              </button>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
