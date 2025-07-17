declare const __IS_NODE__: boolean;
declare const __IS_BROWSER__: boolean;

const isNode = __IS_NODE__;
// const isBrowser = __IS_BROWSER__;

// Type-safe approach for optional dependencies
interface NodeModules {
  Database?: any;
  path?: any;
  os?: any;
  fs?: any;
}

// Global modules container
const nodeModules: NodeModules = {};

// const isNode = (() => {
//   try {
//     return (
//       typeof process !== 'undefined' &&
//       typeof process.versions !== 'undefined' &&
//       typeof process.versions.node !== 'undefined'
//     );
//   } catch {
//     return false;
//   }
// })();

// Async function to load Node.js dependencies
async function loadNodeDependencies(): Promise<boolean> {
  if (!isNode) return false;

  try {
    // Use dynamic imports for both CJS and ESM compatibility
    const [sqliteModule, pathModule, osModule, fsModule] = await Promise.all([
      import('better-sqlite3').catch(() => null),
      import('path').catch(() => null),
      import('os').catch(() => null),
      import('fs').catch(() => null),
    ]);

    if (sqliteModule && pathModule && osModule && fsModule) {
      // Handle both default and named exports for better-sqlite3
      nodeModules.Database = sqliteModule.default || sqliteModule;
      nodeModules.path = pathModule;
      nodeModules.os = osModule;
      nodeModules.fs = fsModule;
      return true;
    }

    return false;
  } catch (error) {
    // Don't log warning here - let the client handle messaging
    return false;
  }
}

interface AgentRecord {
  agent_id: string;
  agent_path: string;
  host: string;
  port: number;
  framework?: string;
  status: string;
  deployed_at: string;
  last_run?: string;
  run_count: number;
  success_count: number;
  error_count: number;
  created_at: string;
  updated_at: string;
}

function isNodeEnvironmentReady(): boolean {
  return !!(
    nodeModules.Database &&
    nodeModules.path &&
    nodeModules.os &&
    nodeModules.fs
  );
}

export class RunAgentRegistry {
  private db: any = null;
  private dbPath: string;
  private initialized: boolean = false;

  constructor(cacheDir?: string) {
    if (!isNode) {
      throw new Error(
        'RunAgentRegistry is only available in Node.js environment'
      );
    }

    // Store cache dir for later initialization
    this.dbPath = cacheDir || '';
  }

  /**
   * Initialize the registry (must be called before use)
   */
  async initialize(): Promise<void> {
    if (this.initialized) return;

    const dependenciesLoaded = await loadNodeDependencies();
    if (!dependenciesLoaded || !isNodeEnvironmentReady()) {
      throw new Error(
        'Required dependencies not available. Install with: npm install better-sqlite3'
      );
    }

    // Set default cache dir if not provided
    if (!this.dbPath) {
      this.dbPath = nodeModules.path.join(
        nodeModules.os.homedir(),
        '.runagent'
      );
    }

    const dbFile = nodeModules.path.join(this.dbPath, 'runagent_local.db');

    // Ensure directory exists
    if (!nodeModules.fs.existsSync(this.dbPath)) {
      nodeModules.fs.mkdirSync(this.dbPath, { recursive: true });
    }
    // INSERT_YOUR_CODE
    if (nodeModules.fs.existsSync(dbFile)) {
      console.log(`[RunAgentRegistry] Found existing database at: ${dbFile}`);
    } else {
      console.log(
        `[RunAgentRegistry] No database found at: ${dbFile}, will create new one.`
      );
    }
    this.db = new nodeModules.Database(dbFile);

    // Enable foreign keys (important for CASCADE deletes)
    this.db.pragma('foreign_keys = ON');

    // Create tables if they don't exist
    this.initializeTables();

    this.initialized = true;
  }

  /**
   * Create database tables
   */
  private initializeTables(): void {
    if (!this.db) return;

    this.db.exec(`
        CREATE TABLE IF NOT EXISTS agents (
          agent_id TEXT PRIMARY KEY,
          agent_path TEXT NOT NULL,
          host TEXT NOT NULL,
          port INTEGER NOT NULL,
          framework TEXT,
          status TEXT NOT NULL DEFAULT 'deployed',
          deployed_at TEXT NOT NULL DEFAULT (datetime('now')),
          last_run TEXT,
          run_count INTEGER NOT NULL DEFAULT 0,
          success_count INTEGER NOT NULL DEFAULT 0,
          error_count INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL DEFAULT (datetime('now')),
          updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        
        CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);
        CREATE INDEX IF NOT EXISTS idx_agents_updated_at ON agents(updated_at);
      `);
  }

  /**
   * Ensure registry is initialized before operations
   */
  private ensureInitialized(): void {
    if (!this.initialized || !this.db) {
      throw new Error('Registry not initialized. Call initialize() first.');
    }
  }

  /**
   * Look up agent by ID - main method for RunAgentClient
   */
  lookupAgent(agentId: string): { host: string; port: number } {
    this.ensureInitialized();

    const stmt = this.db.prepare(`
        SELECT host, port, status, agent_path
        FROM agents 
        WHERE agent_id = ?
      `);

    const agent = stmt.get(agentId) as AgentRecord | undefined;

    if (!agent) {
      throw new Error(`Agent ${agentId} not found in registry`);
    }

    // if (agent.status !== 'deployed') {
    //   throw new Error(
    //     `Agent ${agentId} is not deployed (status: ${agent.status})`
    //   );
    // }

    return {
      host: agent.host,
      port: agent.port,
    };
  }

  /**
   * List all deployed agents
   */
  listDeployedAgents(): AgentRecord[] {
    this.ensureInitialized();

    const stmt = this.db.prepare(`
        SELECT * FROM agents 
        WHERE status = 'deployed' 
        ORDER BY updated_at DESC
      `);

    return stmt.all() as AgentRecord[];
  }

  /**
   * Check if agent exists and is accessible
   */
  async pingAgent(agentId: string): Promise<boolean> {
    try {
      const { host, port } = this.lookupAgent(agentId);

      // Create AbortController for timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);

      try {
        const response = await fetch(`http://${host}:${port}/api/v1/health`, {
          method: 'GET',
          signal: controller.signal,
        });

        clearTimeout(timeoutId);
        return response.ok;
      } catch (fetchError) {
        clearTimeout(timeoutId);
        return false;
      }
    } catch (error) {
      return false;
    }
  }

  /**
   * Update agent's last_run timestamp
   */
  updateLastRun(agentId: string): void {
    this.ensureInitialized();

    const stmt = this.db.prepare(`
        UPDATE agents 
        SET last_run = datetime('now'),
            run_count = run_count + 1,
            updated_at = datetime('now')
        WHERE agent_id = ?
      `);

    stmt.run(agentId);
  }

  /**
   * Record successful run
   */
  recordSuccess(agentId: string): void {
    this.ensureInitialized();

    const stmt = this.db.prepare(`
        UPDATE agents 
        SET success_count = success_count + 1,
            updated_at = datetime('now')
        WHERE agent_id = ?
      `);

    stmt.run(agentId);
  }

  /**
   * Record failed run
   */
  recordError(agentId: string): void {
    this.ensureInitialized();

    const stmt = this.db.prepare(`
        UPDATE agents 
        SET error_count = error_count + 1,
            updated_at = datetime('now')
        WHERE agent_id = ?
      `);

    stmt.run(agentId);
  }

  /**
   * Close database connection
   */
  close(): void {
    if (this.db) {
      this.db.close();
      this.db = null;
    }
    this.initialized = false;
  }

  /**
   * Static method to check if registry features are available
   */
  static async isAvailable(): Promise<boolean> {
    if (!isNode) return false;
    return await loadNodeDependencies();
  }
}

// Export types for use in other files
export type { AgentRecord };
