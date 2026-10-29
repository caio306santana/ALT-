import type { StreamEvent } from "../../../packages/shared-types";
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
      exportMemories(): Promise<{ saved: boolean }>;
      setAnthropicKey(
        key: string,
      ): Promise<{ configured: boolean; verified?: boolean; message?: string }>;
      layout(options: {
        width: number;
        height: number;
        position: string;
      }): Promise<unknown>;
      gameMode(
        enabled: boolean,
      ): Promise<{
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
    };
  }
}
export {};
