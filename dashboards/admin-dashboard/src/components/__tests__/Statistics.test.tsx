import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import Statistics from "../Statistics";
import { DashboardStats } from "../../types";

describe("Statistics Component", () => {
  const mockStats: DashboardStats = {
    users: {
      total: 15,
      active_sessions: 3,
      new_this_month: 2,
    },
    tags: {
      total_active: 10,
      infants: 6,
      mothers: 4,
    },
    alerts: {
      today: 5,
      unacknowledged: 1,
    },
  };

  it("renders loading state when stats are null", () => {
    // We pass null for stats
    render(<Statistics stats={null} />);

    // According to implementation:
    // Total Users -> 0
    // Active Tags -> 0, "Loading..."
    // Alerts Today -> 0

    expect(screen.getByText("Loading...")).toBeInTheDocument();

    const zeros = screen.getAllByText("0");
    expect(zeros.length).toBeGreaterThanOrEqual(1);
  });

  it("renders stats correctly when provided", () => {
    render(<Statistics stats={mockStats} />);

    // Check Total Users
    expect(screen.getByText("15")).toBeInTheDocument();
    expect(screen.getByText("+2 this month")).toBeInTheDocument();

    // Check Active Tags
    expect(screen.getByText("10")).toBeInTheDocument();
    expect(screen.getByText("6 infants, 4 mothers")).toBeInTheDocument();

    // Check Alerts
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("1 unacknowledged")).toBeInTheDocument();
  });

  it("handles zero values correctly", () => {
    const zeroStats: DashboardStats = {
      users: { total: 0, active_sessions: 0, new_this_month: 0 },
      tags: { total_active: 0, infants: 0, mothers: 0 },
      alerts: { today: 0, unacknowledged: 0 },
    };

    render(<Statistics stats={zeroStats} />);

    // Should show "No new users"
    expect(screen.getByText("No new users")).toBeInTheDocument();

    // Should show "0 infants, 0 mothers"
    expect(screen.getByText("0 infants, 0 mothers")).toBeInTheDocument();

    // Should show "0 unacknowledged"
    expect(screen.getByText("0 unacknowledged")).toBeInTheDocument();
  });
});
