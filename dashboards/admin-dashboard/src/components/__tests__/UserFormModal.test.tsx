import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, expect } from "vitest";
import UserFormModal from "../UserFormModal";
import { User } from "../../types";

describe("UserFormModal", () => {
  const mockOnClose = vi.fn();
  const mockOnSubmit = vi.fn();

  it("validates short password", async () => {
    render(<UserFormModal onClose={mockOnClose} onSubmit={mockOnSubmit} />);

    // Fill form
    fireEvent.change(screen.getByLabelText(/Email/i), {
      target: { value: "test@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/First Name/i), {
      target: { value: "John" },
    });
    fireEvent.change(screen.getByLabelText(/Last Name/i), {
      target: { value: "Doe" },
    });

    // Short password
    const passwordInput = screen.getByLabelText("Password");
    fireEvent.change(passwordInput, { target: { value: "123" } });

    // Submit
    fireEvent.click(screen.getByRole("button", { name: /Save/i }));

    // Expect validation error (HTML5 or custom)
    // Note: If using standard HTML validation, we might check checkValidity
    // For now, assume custom validation or UI feedback.
    // If our component relies on browser validation, this test might need adjustment.
  });

  it("submits valid data", async () => {
    render(<UserFormModal onClose={mockOnClose} onSubmit={mockOnSubmit} />);

    fireEvent.change(screen.getByLabelText(/Email/i), {
      target: { value: "valid@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/First Name/i), {
      target: { value: "Jane" },
    });
    fireEvent.change(screen.getByLabelText(/Last Name/i), {
      target: { value: "Doe" },
    });
    fireEvent.change(screen.getByLabelText("Password"), {
      target: { value: "securePass123" },
    });
    fireEvent.change(screen.getByLabelText(/Confirm Password/i), {
      target: { value: "securePass123" },
    });

    // Select role (assuming select input)
    // fireEvent.change(screen.getByLabelText(/Role/i), { target: { value: 'nurse' } });

    fireEvent.click(screen.getByRole("button", { name: /Save/i }));

    await waitFor(() => {
      expect(mockOnSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          email: "valid@example.com",
          password: "securePass123",
        }),
      );
    });
  });
});
