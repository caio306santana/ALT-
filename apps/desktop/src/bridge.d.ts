import type { StreamEvent } from "../../../packages/shared-types";
export type ReleaseCheck = {
  available: boolean;
  reason?: string;
  version?: string;
  name?: string;
  notes?: string;
  published_at?: string;
  page?: string;
  downloadable?: boolean;
  installer?: { name: string; size: number } | null;
};
declare global {
  interface Window {
    alt: {
      request<T = unknown>(
        method: string,
        route: string,
        body?: unknown,
      ): Promise<T>;
      stream(
        id: string,
        kind: "chat" | "pull",
        body: unknown,
        callback: (event: StreamEvent) => void,
      ): Promise<void>;
      window(action: string): Promise<boolean | undefined>;
      installOllama(): Promise<{ ok: boolean; message: string }>;
      ollamaWebsite(): Promise<void>;
      chooseWorkspace(): Promise<unknown>;
      grantWindows(level: 3 | 4, scopeId: string): Promise<unknown>;
      exportMemories(): Promise<{ saved: boolean }>;
      importMemories():Promise<{imported:number;skipped:number}|null>;
      savePolicy(body:import('./components/WorkspacePanels').OwnerPolicy):Promise<unknown>;
      chooseProgram():Promise<unknown>;
      setAnthropicKey(
        key: string,
      ): Promise<{ configured: boolean; verified?: boolean; message?: string }>;
      layout(options: {
        width: number;
        height: number;
        position: string;
      }): Promise<unknown>;
      gameMode(enabled: boolean): Promise<{
        enabled: boolean;
        message: string;
        model_unloaded?: boolean;
      }>;
      openReleases(): Promise<void>;
      verifyUpdate(): Promise<{
        version: string;
        file: string;
        sha256: string;
        size: number;
      } | null>;
      applyUpdate(): Promise<{ started: boolean }>;
      checkUpdate(): Promise<ReleaseCheck>;
      downloadUpdate(): Promise<{
        version: string;
        file: string;
        sha256: string;
        size: number;
      }>;
      onUpdate(
        callback: (
          kind: "available" | "progress",
          info: ReleaseCheck | { received: number; total: number },
        ) => void,
      ): () => void;
      importDocument(
        projectId: string,
      ): Promise<{ id: string; chunks?: number; name?: string; duplicate: boolean } | null>;
    };
  }
}
export {};
