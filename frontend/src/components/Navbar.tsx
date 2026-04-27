export type Page = "dashboard" | "transactions" | "cases" | "reports";

interface NavbarProps {
  activePage: Page;
  onNavigate: (page: Page) => void;
  onLogout: () => void;
}

const items: Array<{ page: Page; label: string; icon: string }> = [
  { page: "dashboard", label: "Dashboard", icon: "BG" },
  { page: "transactions", label: "Transactions", icon: "TX" },
  { page: "cases", label: "Cases", icon: "CS" },
  { page: "reports", label: "Reports", icon: "RP" },
];

export default function Navbar({ activePage, onNavigate, onLogout }: NavbarProps) {
  return (
    <aside className="navbar">
      <div className="brand">
        <div className="brand-mark">B</div>
        <div>
          <strong>BankGuard AI</strong>
          <span>Fraud Detection</span>
        </div>
      </div>

      <nav className="nav-items" aria-label="Primary navigation">
        {items.map((item) => (
          <button
            className={activePage === item.page ? "nav-item active" : "nav-item"}
            key={item.page}
            onClick={() => onNavigate(item.page)}
            type="button"
          >
            <span>{item.icon}</span>
            {item.label}
          </button>
        ))}
      </nav>

      <div className="navbar-footer">
        <div className="demo-user">
          <span>analyst@bankguard.ai</span>
          <strong>Fraud Analyst</strong>
        </div>
        <button className="ghost-button" onClick={onLogout} type="button">
          Sign out
        </button>
      </div>
    </aside>
  );
}

