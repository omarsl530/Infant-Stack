import React from 'react';
import { ShieldCheckIcon } from '@heroicons/react/24/outline';

const PermissionMatrix: React.FC = () => {
  // This matches the backend ROLE_PERMISSIONS constant in auth.py
  const permissions = {
    'User Management': [
      { id: 'user:read', label: 'View Users', roles: ['admin', 'nurse'] },
      { id: 'user:write', label: 'Create/Edit Users', roles: ['admin'] },
      { id: 'user:delete', label: 'Delete Users', roles: ['admin'] },
    ],
    'Patient Management': [
      { id: 'patient:read', label: 'View Patients', roles: ['admin', 'nurse', 'security', 'viewer'] },
      { id: 'patient:write', label: 'Edit Patients', roles: ['admin', 'nurse'] },
      { id: 'patient:admit', label: 'Admit Patients', roles: ['admin', 'nurse'] },
      { id: 'patient:discharge', label: 'Discharge', roles: ['admin', 'nurse'] },
    ],
    'Security & RTLS': [
      { id: 'gate:read', label: 'View Gates', roles: ['admin', 'nurse', 'security', 'viewer'] },
      { id: 'gate:control', label: 'Control Gates', roles: ['admin', 'security'] },
      { id: 'rtls:read', label: 'View Live Locations', roles: ['admin', 'nurse', 'security', 'viewer'] },
      { id: 'rtls:history', label: 'View Location History', roles: ['admin', 'nurse', 'security'] },
    ],
    'System': [
      { id: 'audit:read', label: 'View Audit Logs', roles: ['admin', 'security'] },
      { id: 'system:config', label: 'System Configuration', roles: ['admin'] },
    ]
  };

  const roles = [
    { id: 'admin', label: 'Admin', color: 'purple' },
    { id: 'nurse', label: 'Nurse', color: 'blue' },
    { id: 'security', label: 'Security', color: 'orange' },
    { id: 'viewer', label: 'Viewer', color: 'slate' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
           <h2 className="text-2xl font-bold text-gray-800 dark:text-white">Role Permissions</h2>
           <p className="text-slate-500 mt-1">Matrix view of system access levels by role.</p>
        </div>
      </div>

      <div className="bg-white dark:bg-slate-800 shadow rounded-lg overflow-hidden border border-gray-200 dark:border-slate-700">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-slate-700">
            <thead className="bg-gray-50 dark:bg-slate-900/50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider w-1/3">
                  Permission
                </th>
                {roles.map(role => (
                  <th key={role.id} className="px-6 py-3 text-center text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider">
                    <span className={`badge badge-${role.id} mx-auto block w-max`}>{role.label}</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-slate-800 divide-y divide-gray-200 dark:divide-slate-700">
              {Object.entries(permissions).map(([category, items]) => (
                <React.Fragment key={category}>
                  <tr className="bg-gray-50 dark:bg-slate-900/30">
                    <td colSpan={roles.length + 1} className="px-6 py-2 text-xs font-semibold text-gray-700 dark:text-slate-300 uppercase tracking-wider">
                      {category}
                    </td>
                  </tr>
                  {items.map((item) => (
                    <tr key={item.id} className="hover:bg-gray-50 dark:hover:bg-slate-700/30 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-200">
                        <div className="flex items-center">
                          <ShieldCheckIcon className="w-4 h-4 text-gray-400 mr-2" />
                          <div>
                            <div className="font-medium">{item.label}</div>
                            <div className="text-xs text-gray-500 font-mono">{item.id}</div>
                          </div>
                        </div>
                      </td>
                      {roles.map(role => {
                        const hasPermission = item.roles.includes(role.id);
                        return (
                          <td key={`${item.id}-${role.id}`} className="px-6 py-4 whitespace-nowrap text-center text-sm">
                            {hasPermission ? (
                              <svg className="w-5 h-5 text-green-500 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                              </svg>
                            ) : (
                              <div className="w-1.5 h-1.5 bg-gray-200 dark:bg-slate-600 rounded-full mx-auto" aria-hidden="true" />
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      
      <div className="bg-amber-50 dark:bg-amber-900/10 border-l-4 border-amber-400 p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-amber-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <p className="text-sm text-amber-700 dark:text-amber-200">
              Role permissions are defined in the backend configuration and cannot be modified without deployment.
              Roles can be assigned to users in the <span className="font-semibold">Users</span> tab.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PermissionMatrix;
