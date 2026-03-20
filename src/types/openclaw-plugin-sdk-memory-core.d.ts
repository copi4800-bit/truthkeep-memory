declare module "openclaw/plugin-sdk/memory-core" {
  export type OpenClawPluginToolContext = {
    agentId?: string;
    workspaceDir?: string;
    sessionKey?: string;
    sessionFile?: string;
    config?: unknown;
  };

  export type OpenClawPluginApi = {
    config?: {
      agents?: {
        defaults?: {
          workspace?: string;
        };
      };
    };
    pluginConfig?: unknown;
    logger: {
      info(message: string): void;
      warn(message: string): void;
    };
    resolvePath(input: string): string;
    registerTool(
      factory: (ctx: OpenClawPluginToolContext) => unknown,
      options?: unknown,
    ): void;
    on(event: string, handler: (event: any, ctx: any) => Promise<unknown> | unknown): void;
    registerService(service: {
      id: string;
      start?: () => void | Promise<void>;
      stop?: () => void | Promise<void>;
    }): void;
  };
}
