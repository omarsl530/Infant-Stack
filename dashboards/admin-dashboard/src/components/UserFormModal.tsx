import React, { useState } from "react";
import { XMarkIcon } from "@heroicons/react/24/outline";
import { User, Role } from "../types";

interface UserFormModalProps {
  user?: User;
  roles?: Role[];
  onClose: () => void;
  onSubmit: (data: Partial<User> & { password?: string }) => Promise<void>;
}

const UserFormModal: React.FC<UserFormModalProps> = ({
  user,
  roles = [],
  onClose,
  onSubmit,
}) => {
  const [formData, setFormData] = useState({
    email: user?.email || "",
    first_name: user?.first_name || "",
    last_name: user?.last_name || "",
    role: user?.role || "viewer",
    password: "",
    confirmPassword: "",
    is_active: user ? user.is_active : true,
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!user && !formData.password) {
      setError("Password is required for new users");
      return;
    }

    if (formData.password && formData.password !== formData.confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    setIsSubmitting(true);
    try {
      const submitData: any = {
        email: formData.email,
        first_name: formData.first_name,
        last_name: formData.last_name,
        role: formData.role,
      };

      if (user) {
        submitData.is_active = formData.is_active;
      }

      if (formData.password) {
        submitData.password = formData.password;
      }

      await onSubmit(submitData);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Failed to save user");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div className="fixed inset-0 transition-opacity" aria-hidden="true">
          <div
            className="absolute inset-0 bg-gray-900/75 backdrop-blur-sm"
            onClick={onClose}
          ></div>
        </div>

        <span
          className="hidden sm:inline-block sm:align-middle sm:h-screen"
          aria-hidden="true"
        >
          &#8203;
        </span>

        <div className="inline-block align-bottom bg-white dark:bg-slate-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
          <div className="absolute top-0 right-0 pt-4 pr-4">
            <button
              onClick={onClose}
              className="bg-white dark:bg-slate-800 rounded-md text-gray-400 hover:text-gray-500 focus:outline-none"
            >
              <span className="sr-only">Close</span>
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
              <h3 className="text-lg leading-6 font-medium text-gray-900 dark:text-white mb-4">
                {user ? "Edit User" : "Add New User"}
              </h3>

              {error && (
                <div className="mb-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-300 px-4 py-3 rounded">
                  {error}
                </div>
              )}

              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label
                      htmlFor="first_name"
                      className="block text-sm font-medium text-gray-700 dark:text-slate-300"
                    >
                      First Name
                    </label>
                    <input
                      id="first_name"
                      type="text"
                      required
                      className="form-input mt-1 block w-full"
                      value={formData.first_name}
                      onChange={(e) =>
                        setFormData({ ...formData, first_name: e.target.value })
                      }
                    />
                  </div>
                  <div>
                    <label
                      htmlFor="last_name"
                      className="block text-sm font-medium text-gray-700 dark:text-slate-300"
                    >
                      Last Name
                    </label>
                    <input
                      id="last_name"
                      type="text"
                      required
                      className="form-input mt-1 block w-full"
                      value={formData.last_name}
                      onChange={(e) =>
                        setFormData({ ...formData, last_name: e.target.value })
                      }
                    />
                  </div>
                </div>

                <div>
                  <label
                    htmlFor="email"
                    className="block text-sm font-medium text-gray-700 dark:text-slate-300"
                  >
                    Email
                  </label>
                  <input
                    id="email"
                    type="email"
                    required
                    className="form-input mt-1 block w-full"
                    value={formData.email}
                    onChange={(e) =>
                      setFormData({ ...formData, email: e.target.value })
                    }
                  />
                </div>

                <div>
                  <label
                    htmlFor="role"
                    className="block text-sm font-medium text-gray-700 dark:text-slate-300"
                  >
                    Role
                  </label>
                  <select
                    id="role"
                    className="form-select mt-1 block w-full"
                    value={formData.role}
                    onChange={(e) =>
                      setFormData({ ...formData, role: e.target.value as any })
                    }
                  >
                    {!formData.role && <option value="">Select a role</option>}
                    {roles.length > 0 ? (
                      roles.map((role) => (
                        <option key={role.id} value={role.name}>
                          {role.name}
                        </option>
                      ))
                    ) : (
                      <>
                        <option value="viewer">Viewer</option>
                        <option value="nurse">Nurse</option>
                        <option value="security">Security</option>
                        <option value="admin">Admin</option>
                      </>
                    )}
                  </select>
                </div>

                {!user && (
                  <>
                    <div>
                      <label
                        htmlFor="password"
                        className="block text-sm font-medium text-gray-700 dark:text-slate-300"
                      >
                        Password
                      </label>
                      <input
                        id="password"
                        type="password"
                        required={!user}
                        className="form-input mt-1 block w-full"
                        value={formData.password}
                        onChange={(e) =>
                          setFormData({ ...formData, password: e.target.value })
                        }
                      />
                    </div>
                    <div>
                      <label
                        htmlFor="confirmPassword"
                        className="block text-sm font-medium text-gray-700 dark:text-slate-300"
                      >
                        Confirm Password
                      </label>
                      <input
                        id="confirmPassword"
                        type="password"
                        required={!user}
                        className="form-input mt-1 block w-full"
                        value={formData.confirmPassword}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            confirmPassword: e.target.value,
                          })
                        }
                      />
                    </div>
                  </>
                )}

                <div className="flex items-center mt-4">
                  <input
                    id="is_active"
                    type="checkbox"
                    className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                    checked={formData.is_active}
                    onChange={(e) =>
                      setFormData({ ...formData, is_active: e.target.checked })
                    }
                  />
                  <label
                    htmlFor="is_active"
                    className="ml-2 block text-sm text-gray-900 dark:text-slate-300"
                  >
                    Active Account
                  </label>
                </div>
              </div>
            </div>

            <div className="bg-gray-50 dark:bg-slate-800/50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse border-t border-gray-200 dark:border-slate-700">
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:ml-3 sm:w-auto sm:text-sm disabled:opacity-50"
              >
                {isSubmitting ? "Saving..." : "Save"}
              </button>
              <button
                type="button"
                className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
                onClick={onClose}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default UserFormModal;
