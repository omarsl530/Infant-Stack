import React, { useState, useEffect } from "react";
import {
  PlusIcon,
  PencilSquareIcon,
  MagnifyingGlassIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import { ConfigResponse, ConfigType } from "../types";
import { fetchConfig, updateConfig, createConfig } from "../api";

const ConfigEditor: React.FC = () => {
  const [configs, setConfigs] = useState<ConfigResponse[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  // Modal State
  const [showModal, setShowModal] = useState(false);
  const [editingConfig, setEditingConfig] = useState<ConfigResponse | null>(
    null,
  );

  // Form State
  const [formData, setFormData] = useState<{
    key: string;
    value: string;
    type: ConfigType;
    description: string;
    is_public: boolean;
  }>({
    key: "",
    value: "",
    type: "string",
    description: "",
    is_public: false,
  });

  useEffect(() => {
    loadConfigs();
  }, []);

  const loadConfigs = async () => {
    setLoading(true);
    try {
      const data = await fetchConfig();
      setConfigs(data);
    } catch (err) {
      console.error("Failed to load configs", err);
    } finally {
      setLoading(false);
    }
  };

  const filteredConfigs = configs.filter(
    (c) =>
      c.key.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.description &&
        c.description.toLowerCase().includes(searchQuery.toLowerCase())),
  );

  const handleEdit = (config: ConfigResponse) => {
    setEditingConfig(config);
    setFormData({
      key: config.key,
      value: String(config.value),
      type: config.type,
      description: config.description || "",
      is_public: config.is_public,
    });
    setShowModal(true);
  };

  const handleCreate = () => {
    setEditingConfig(null);
    setFormData({
      key: "",
      value: "",
      type: "string",
      description: "",
      is_public: false,
    });
    setShowModal(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingConfig) {
        // Update
        const updated = await updateConfig(editingConfig.key, {
          value: formData.value,
          description: formData.description,
        });
        setConfigs(configs.map((c) => (c.key === updated.key ? updated : c)));
      } else {
        // Create
        const created = await createConfig({
          key: formData.key,
          value: formData.value,
          type: formData.type,
          description: formData.description,
          is_public: formData.is_public,
        });
        setConfigs([...configs, created]);
      }
      setShowModal(false);
    } catch (err) {
      console.error("Failed to save config", err);
      // Ideally show error toast
      alert(
        "Failed to save configuration. Key might already exist or value format is invalid.",
      );
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
          <input
            type="text"
            placeholder="Search settings..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="form-input pl-10"
          />
        </div>
        <button className="btn-primary" onClick={handleCreate}>
          <PlusIcon className="w-5 h-5 mr-2" />
          Add Setting
        </button>
      </div>

      <div className="glass-card overflow-hidden">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Key</th>
              <th>Value</th>
              <th>Type</th>
              <th>Description</th>
              <th>Visibility</th>
              <th className="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="text-center py-8 text-slate-400">
                  Loading configurations...
                </td>
              </tr>
            ) : filteredConfigs.length === 0 ? (
              <tr>
                <td colSpan={6} className="text-center py-8 text-slate-400">
                  No settings found.
                </td>
              </tr>
            ) : (
              filteredConfigs.map((config) => (
                <tr key={config.key}>
                  <td className="font-mono text-admin-400 font-medium">
                    {config.key}
                  </td>
                  <td
                    className="max-w-xs truncate"
                    title={String(config.value)}
                  >
                    {String(config.value)}
                  </td>
                  <td>
                    <span className="badge bg-slate-700 text-slate-300">
                      {config.type}
                    </span>
                  </td>
                  <td className="text-slate-400">
                    {config.description || "-"}
                  </td>
                  <td>
                    {config.is_public ? (
                      <span className="text-xs bg-emerald-900/30 text-emerald-400 px-2 py-0.5 rounded border border-emerald-800">
                        Public
                      </span>
                    ) : (
                      <span className="text-xs bg-slate-700/50 text-slate-400 px-2 py-0.5 rounded border border-slate-600">
                        Internal
                      </span>
                    )}
                  </td>
                  <td className="text-right">
                    <button
                      onClick={() => handleEdit(config)}
                      className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-700 rounded"
                      title="Edit"
                    >
                      <PencilSquareIcon className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex items-center justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div
              className="fixed inset-0 transition-opacity"
              aria-hidden="true"
            >
              <div
                className="absolute inset-0 bg-gray-900/75 backdrop-blur-sm"
                onClick={() => setShowModal(false)}
              ></div>
            </div>
            <span
              className="hidden sm:inline-block sm:align-middle sm:h-screen"
              aria-hidden="true"
            >
              &#8203;
            </span>

            <div className="inline-block align-bottom bg-surface-card rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full border border-slate-700">
              <div className="absolute top-0 right-0 pt-4 pr-4">
                <button
                  onClick={() => setShowModal(false)}
                  className="text-slate-400 hover:text-white"
                >
                  <XMarkIcon className="w-6 h-6" />
                </button>
              </div>

              <form onSubmit={handleSubmit} className="p-6">
                <h3 className="text-lg font-medium text-white mb-4">
                  {editingConfig ? "Edit Setting" : "New Setting"}
                </h3>

                <div className="space-y-4">
                  <div>
                    <label className="form-label">Key</label>
                    <input
                      type="text"
                      className="form-input disabled:opacity-50 disabled:cursor-not-allowed"
                      value={formData.key}
                      onChange={(e) =>
                        setFormData({ ...formData, key: e.target.value })
                      }
                      disabled={!!editingConfig}
                      required
                      placeholder="e.g., system.alert_timeout_ms"
                    />
                  </div>

                  <div>
                    <label className="form-label">Type</label>
                    <select
                      className="form-select disabled:opacity-50"
                      value={formData.type}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          type: e.target.value as ConfigType,
                        })
                      }
                      disabled={!!editingConfig}
                    >
                      <option value="string">String</option>
                      <option value="integer">Integer</option>
                      <option value="float">Float</option>
                      <option value="boolean">Boolean</option>
                      <option value="json">JSON</option>
                    </select>
                  </div>

                  <div>
                    <label className="form-label">Value</label>
                    <input
                      type="text"
                      className="form-input"
                      value={formData.value}
                      onChange={(e) =>
                        setFormData({ ...formData, value: e.target.value })
                      }
                      required
                    />
                    {formData.type === "boolean" && (
                      <p className="text-xs text-slate-500 mt-1">
                        Use "true" or "false"
                      </p>
                    )}
                  </div>

                  <div>
                    <label className="form-label">Description</label>
                    <textarea
                      className="form-textarea"
                      rows={2}
                      value={formData.description}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          description: e.target.value,
                        })
                      }
                      placeholder="Brief description of what this setting controls..."
                    />
                  </div>

                  {!editingConfig && (
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        id="is_public"
                        checked={formData.is_public}
                        onChange={(e) =>
                          setFormData({
                            ...formData,
                            is_public: e.target.checked,
                          })
                        }
                        className="rounded border-slate-600 bg-slate-800 text-admin-500 focus:ring-admin-500"
                      />
                      <label
                        htmlFor="is_public"
                        className="text-sm text-slate-300"
                      >
                        Public (Exposed to unauthenticated clients)
                      </label>
                    </div>
                  )}
                </div>

                <div className="mt-6 flex justify-end gap-3">
                  <button
                    type="button"
                    onClick={() => setShowModal(false)}
                    className="btn-secondary"
                  >
                    Cancel
                  </button>
                  <button type="submit" className="btn-primary">
                    Save Changes
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ConfigEditor;
