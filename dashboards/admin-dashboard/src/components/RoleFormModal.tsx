import React, { useState, useEffect } from 'react';
import { XMarkIcon, CheckCircleIcon } from '@heroicons/react/24/outline';
import { Role, RoleCreate, RoleUpdate } from '../types';
import { fetchAvailablePermissions } from '../api';

interface RoleFormModalProps {
  role?: Role;
  onClose: () => void;
  onSubmit: (data: RoleCreate | RoleUpdate) => Promise<void>;
}

const RoleFormModal: React.FC<RoleFormModalProps> = ({ role, onClose, onSubmit }) => {
  const [formData, setFormData] = useState<{
    name: string;
    description: string;
    permissions: Record<string, string[]>;
  }>({
    name: role?.name || '',
    description: role?.description || '',
    permissions: role?.permissions || {},
  });

  const [availablePermissions, setAvailablePermissions] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    loadPermissions();
  }, []);

  const loadPermissions = async () => {
    try {
      const perms = await fetchAvailablePermissions();
      setAvailablePermissions(perms);
    } catch (err) {
      console.error('Failed to load permissions', err);
      setError('Failed to load available permissions');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await onSubmit(formData);
    } catch (err) {
      setError('Failed to save role');
    } finally {
      setIsSubmitting(false);
    }
  };

  const togglePermission = (permString: string) => {
    const [resource, action] = permString.split(':');
    if (!resource || !action) return;

    setFormData(prev => {
      const currentPerms = { ...prev.permissions };
      const resourceActions = currentPerms[resource] || [];
      
      let newResourceActions;
      if (resourceActions.includes(action)) {
        newResourceActions = resourceActions.filter(a => a !== action);
      } else {
        newResourceActions = [...resourceActions, action];
      }

      if (newResourceActions.length === 0) {
        delete currentPerms[resource];
      } else {
        currentPerms[resource] = newResourceActions;
      }

      return { ...prev, permissions: currentPerms };
    });
  };

  // Group permissions by resource for display
  const groupedPermissions = availablePermissions.reduce((acc, perm) => {
    const [resource, action] = perm.split(':');
    if (!acc[resource]) acc[resource] = [];
    acc[resource].push(action);
    return acc;
  }, {} as Record<string, string[]>);

  const isPermSelected = (permString: string) => {
    const [resource, action] = permString.split(':');
    return formData.permissions[resource]?.includes(action);
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div className="fixed inset-0 transition-opacity" aria-hidden="true">
          <div className="absolute inset-0 bg-gray-900/75 backdrop-blur-sm" onClick={onClose}></div>
        </div>

        <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>

        <div className="inline-block align-bottom bg-white dark:bg-slate-800 rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-2xl sm:w-full">
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
                {role ? 'Edit Role' : 'Create New Role'}
              </h3>

              {error && (
                <div className="mb-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-600 dark:text-red-300 px-4 py-3 rounded">
                  {error}
                </div>
              )}

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-300">Role Name</label>
                  <input
                    type="text"
                    required
                    disabled={role?.is_system} // Cannot rename system roles
                    className="form-input mt-1 block w-full disabled:opacity-50"
                    value={formData.name}
                    onChange={e => setFormData({ ...formData, name: e.target.value })}
                  />
                  {role?.is_system && <p className="text-xs text-amber-500 mt-1">System roles cannot be renamed.</p>}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-300">Description</label>
                  <input
                    type="text"
                    className="form-input mt-1 block w-full"
                    value={formData.description}
                    onChange={e => setFormData({ ...formData, description: e.target.value })}
                  />
                </div>

                <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-2">Permissions</label>
                    <div className="border border-gray-200 dark:border-slate-700 rounded-md p-4 max-h-96 overflow-y-auto">
                        {Object.entries(groupedPermissions).map(([resource, actions]) => (
                            <div key={resource} className="mb-4 last:mb-0">
                                <h4 className="text-sm font-semibold text-gray-900 dark:text-white capitalize mb-2 border-b border-gray-100 dark:border-slate-700 pb-1">
                                    {resource}
                                </h4>
                                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                                    {actions.map(action => {
                                        const permString = `${resource}:${action}`;
                                        const selected = isPermSelected(permString);
                                        return (
                                            <div 
                                                key={permString}
                                                onClick={() => togglePermission(permString)}
                                                className={`
                                                    cursor-pointer px-3 py-2 rounded text-xs font-medium border flex items-center gap-2 transition-colors
                                                    ${selected 
                                                        ? 'bg-indigo-50 border-indigo-200 text-indigo-700 dark:bg-indigo-900/30 dark:border-indigo-700 dark:text-indigo-300' 
                                                        : 'bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-700'
                                                    }
                                                `}
                                            >
                                                <div className={`w-4 h-4 rounded-full border flex items-center justify-center ${selected ? 'bg-indigo-500 border-indigo-500' : 'bg-white border-gray-300 dark:bg-slate-900 dark:border-slate-600'}`}>
                                                    {selected && <CheckCircleIcon className="w-3 h-3 text-white" />}
                                                </div>
                                                {action}
                                            </div>
                                        );
                                    })}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

              </div>
            </div>

            <div className="bg-gray-50 dark:bg-slate-800/50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse border-t border-gray-200 dark:border-slate-700">
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:ml-3 sm:w-auto sm:text-sm disabled:opacity-50"
              >
                {isSubmitting ? 'Saving...' : 'Save'}
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

export default RoleFormModal;
