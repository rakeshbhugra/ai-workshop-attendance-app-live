/**
 * Upload/download against the ObjectStorage-backed endpoints.
 *
 * Deliberately small: it exists to prove the storage seam works end to end and
 * to show the multipart upload idiom (`api.upload`). The uploaded keys are kept
 * in component state — a real app would record them against a domain entity.
 */

import { useState } from "react";
import { Upload } from "lucide-react";
import { ApiError, api } from "@/lib/api";
import { useUiStore } from "@/stores/ui-store";

export function FilesPage() {
  const notify = useUiStore((s) => s.notify);
  const [keys, setKeys] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);

  async function handleUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const { key } = await api.upload<{ key: string }>("/files", file);
      setKeys((current) => [key, ...current]);
      notify(`Uploaded ${file.name}`);
    } catch (err) {
      notify(
        err instanceof ApiError && err.isUserFixable ? err.detail : "Upload failed.",
        "error",
      );
    } finally {
      setUploading(false);
      // Reset the input so re-picking the same file fires onChange again.
      event.target.value = "";
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">Files</h1>

      <label className="flex w-fit cursor-pointer items-center gap-2 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white dark:bg-slate-100 dark:text-slate-900">
        <Upload size={15} />
        {uploading ? "Uploading…" : "Choose a file"}
        <input type="file" onChange={handleUpload} disabled={uploading} className="hidden" />
      </label>

      {keys.length === 0 ? (
        <p className="text-sm text-slate-500">
          Nothing uploaded yet. Files go to in-memory storage by default, or to
          LocalStack&nbsp;S3 when you run <code>make up-aws</code>.
        </p>
      ) : (
        <ul className="space-y-2">
          {keys.map((key) => (
            <li key={key}>
              <a
                href={`/api/v1/files/${key}`}
                target="_blank"
                rel="noreferrer"
                className="text-sm text-blue-600 underline underline-offset-2 dark:text-blue-400"
              >
                {key.split("/").pop()}
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
