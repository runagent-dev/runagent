# runagent/client/local_db.py
import sqlite3
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from rich.console import Console
console = Console()


class LocalDatabase:
    """SQLite database manager for local agent deployments"""
    
    def __init__(self, db_path: str = "runagent_local.db", auto_init: bool = False):
        """
        Initialize the local database
        
        Args:
            db_path: Path to the SQLite database file
            auto_init: Whether to automatically initialize the database
        """
        self.db_path = Path(db_path)
        if auto_init:
            self._init_database()
    
    def _init_database(self):
        """Initialize the database with required tables"""
        console.print(f"🗃️ Initializing database: [blue]{self.db_path}[/blue]")
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS agents (
                    agent_id TEXT PRIMARY KEY,
                    folder_path TEXT NOT NULL,
                    deployment_path TEXT NOT NULL,
                    framework TEXT,
                    status TEXT DEFAULT 'deployed',
                    deployed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_run TIMESTAMP NULL,
                    run_count INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    metadata TEXT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS agent_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    input_data TEXT NOT NULL,
                    output_data TEXT NULL,
                    success BOOLEAN NOT NULL,
                    error_message TEXT NULL,
                    execution_time REAL NULL,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP NULL,
                    FOREIGN KEY (agent_id) REFERENCES agents (agent_id) ON DELETE CASCADE
                )
            ''')
            
            # Create indexes for better performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_agent_runs_agent_id ON agent_runs(agent_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_agent_runs_started_at ON agent_runs(started_at)')
            
            conn.commit()
        
        console.print(f"✅ Database initialized successfully")
    
    def ensure_initialized(self):
        """Ensure database is initialized (create if doesn't exist)"""
        if not self.db_path.exists():
            self._init_database()
        
    def is_initialized(self) -> bool:
        """Check if database file exists and is initialized"""
        if not self.db_path.exists():
            return False
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='agents'")
                return cursor.fetchone() is not None
        except:
            return False
    
    def add_agent(self, agent_id: str, folder_path: str, deployment_path: str, 
                  framework: str = None, metadata: Dict = None) -> Dict:
        """
        Add a new agent to the database with 5-agent cap enforcement
        
        Args:
            agent_id: Unique agent identifier
            folder_path: Original source folder path
            deployment_path: Deployed agent directory path
            framework: Framework type (langchain, langgraph, etc.)
            metadata: Additional metadata as dictionary
            
        Returns:
            Dictionary with success status and details
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check current agent count
                cursor = conn.execute('SELECT COUNT(*) FROM agents')
                current_count = cursor.fetchone()[0]
                
                # Check if agent already exists
                cursor = conn.execute('SELECT agent_id FROM agents WHERE agent_id = ?', (agent_id,))
                existing_agent = cursor.fetchone()
                
                if existing_agent:
                    return {
                        'success': False,
                        'error': f'Agent {agent_id} already exists',
                        'code': 'AGENT_EXISTS'
                    }
                
                # Enforce 5-agent limit
                if current_count >= 5:
                    # Get oldest agent for replacement suggestion
                    cursor = conn.execute('''
                        SELECT agent_id, deployed_at 
                        FROM agents 
                        ORDER BY deployed_at ASC 
                        LIMIT 1
                    ''')
                    oldest_agent = cursor.fetchone()
                    
                    return {
                        'success': False,
                        'error': f'Maximum 5 agents allowed. Database is at capacity ({current_count}/5 agents).',
                        'code': 'DATABASE_FULL',
                        'current_count': current_count,
                        'max_allowed': 5,
                        'oldest_agent': {
                            'agent_id': oldest_agent[0],
                            'deployed_at': oldest_agent[1]
                        } if oldest_agent else None,
                        'suggestion': f'Consider replacing the oldest agent: {oldest_agent[0]}' if oldest_agent else 'Database cleanup needed'
                    }
                
                # Add the new agent
                conn.execute('''
                    INSERT INTO agents 
                    (agent_id, folder_path, deployment_path, framework, metadata)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    agent_id,
                    str(folder_path),
                    str(deployment_path),
                    framework,
                    json.dumps(metadata) if metadata else None
                ))
                conn.commit()
                
                return {
                    'success': True,
                    'message': f'Agent {agent_id} added successfully',
                    'current_count': current_count + 1,
                    'max_allowed': 5,
                    'remaining_slots': 5 - (current_count + 1)
                }
                
        except sqlite3.IntegrityError as e:
            return {
                'success': False,
                'error': f'Database integrity error: {str(e)}',
                'code': 'INTEGRITY_ERROR'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Database error: {str(e)}',
                'code': 'DATABASE_ERROR'
            }
    
    def replace_agent(self, old_agent_id: str, new_agent_id: str, folder_path: str, 
                     deployment_path: str, framework: str = None, metadata: Dict = None) -> Dict:
        """
        Replace an existing agent with a new one (since deletion is not allowed)
        
        Args:
            old_agent_id: Agent ID to replace
            new_agent_id: New agent ID
            folder_path: Original source folder path
            deployment_path: Deployed agent directory path
            framework: Framework type
            metadata: Additional metadata
            
        Returns:
            Dictionary with success status and details
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check if old agent exists
                cursor = conn.execute('SELECT * FROM agents WHERE agent_id = ?', (old_agent_id,))
                old_agent = cursor.fetchone()
                
                if not old_agent:
                    return {
                        'success': False,
                        'error': f'Agent {old_agent_id} not found for replacement',
                        'code': 'AGENT_NOT_FOUND'
                    }
                
                # Check if new agent ID already exists
                cursor = conn.execute('SELECT agent_id FROM agents WHERE agent_id = ?', (new_agent_id,))
                if cursor.fetchone():
                    return {
                        'success': False,
                        'error': f'New agent ID {new_agent_id} already exists',
                        'code': 'NEW_AGENT_EXISTS'
                    }
                
                # Update the existing record (replacement, not deletion)
                conn.execute('''
                    UPDATE agents 
                    SET agent_id = ?, folder_path = ?, deployment_path = ?, 
                        framework = ?, metadata = ?, 
                        deployed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP,
                        status = 'deployed', run_count = 0, success_count = 0, error_count = 0
                    WHERE agent_id = ?
                ''', (
                    new_agent_id,
                    str(folder_path),
                    str(deployment_path),
                    framework,
                    json.dumps(metadata) if metadata else None,
                    old_agent_id
                ))
                
                # Update run records to point to new agent ID
                conn.execute('''
                    UPDATE agent_runs SET agent_id = ? WHERE agent_id = ?
                ''', (new_agent_id, old_agent_id))
                
                conn.commit()
                
                return {
                    'success': True,
                    'message': f'Agent {old_agent_id} replaced with {new_agent_id}',
                    'old_agent_id': old_agent_id,
                    'new_agent_id': new_agent_id,
                    'operation': 'replace'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Replacement failed: {str(e)}',
                'code': 'REPLACE_ERROR'
            }
    
    def delete_agent(self, agent_id: str) -> bool:
        """
        Delete agent from database - DISABLED for this implementation
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Always False since deletion is not allowed
        """
        print(f"⚠️ Agent deletion is disabled. Agent {agent_id} cannot be deleted from database.")
        print(f"💡 Use 'replace_agent()' to replace this agent with a new one.")
        return False
    
    def get_database_capacity_info(self) -> Dict:
        """
        Get database capacity information
        
        Returns:
            Capacity information dictionary
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('SELECT COUNT(*) FROM agents')
                current_count = cursor.fetchone()[0]
                
                # Get agents ordered by deployment date
                cursor = conn.execute('''
                    SELECT agent_id, deployed_at, framework, status 
                    FROM agents 
                    ORDER BY deployed_at ASC
                ''')
                agents = cursor.fetchall()
                
                return {
                    'current_count': current_count,
                    'max_capacity': 5,
                    'remaining_slots': max(0, 5 - current_count),
                    'is_full': current_count >= 5,
                    'agents': [
                        {
                            'agent_id': agent[0],
                            'deployed_at': agent[1],
                            'framework': agent[2],
                            'status': agent[3]
                        }
                        for agent in agents
                    ],
                    'oldest_agent': {
                        'agent_id': agents[0][0],
                        'deployed_at': agents[0][1]
                    } if agents else None,
                    'newest_agent': {
                        'agent_id': agents[-1][0], 
                        'deployed_at': agents[-1][1]
                    } if agents else None
                }
        except Exception as e:
            return {
                'error': f'Failed to get capacity info: {str(e)}',
                'current_count': 0,
                'max_capacity': 5,
                'remaining_slots': 5,
                'is_full': False
            }
    
    def get_agent(self, agent_id: str) -> Optional[Dict]:
        """
        Get agent information from database
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Agent information dictionary or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute('''
                    SELECT * FROM agents WHERE agent_id = ?
                ''', (agent_id,))
                
                row = cursor.fetchone()
                if row:
                    agent_data = dict(row)
                    # Parse metadata JSON
                    if agent_data['metadata']:
                        agent_data['metadata'] = json.loads(agent_data['metadata'])
                    return agent_data
                return None
        except Exception as e:
            print(f"Error getting agent from database: {e}")
            return None
    
    def list_agents(self, status: str = None) -> List[Dict]:
        """
        List all agents, optionally filtered by status
        
        Args:
            status: Optional status filter
            
        Returns:
            List of agent dictionaries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                if status:
                    cursor = conn.execute('''
                        SELECT * FROM agents WHERE status = ? ORDER BY deployed_at DESC
                    ''', (status,))
                else:
                    cursor = conn.execute('''
                        SELECT * FROM agents ORDER BY deployed_at DESC
                    ''')
                
                agents = []
                for row in cursor.fetchall():
                    agent_data = dict(row)
                    # Parse metadata JSON
                    if agent_data['metadata']:
                        agent_data['metadata'] = json.loads(agent_data['metadata'])
                    agents.append(agent_data)
                
                return agents
        except Exception as e:
            print(f"Error listing agents from database: {e}")
            return []
    
    def update_agent_status(self, agent_id: str, status: str) -> bool:
        """
        Update agent status
        
        Args:
            agent_id: Agent identifier
            status: New status
            
        Returns:
            True if successful
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    UPDATE agents 
                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE agent_id = ?
                ''', (status, agent_id))
                conn.commit()
                return conn.total_changes > 0
        except Exception as e:
            print(f"Error updating agent status: {e}")
            return False
    
    def delete_agent(self, agent_id: str) -> bool:
        """
        Delete agent from database
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            True if successful
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('DELETE FROM agents WHERE agent_id = ?', (agent_id,))
                conn.commit()
                return conn.total_changes > 0
        except Exception as e:
            print(f"Error deleting agent: {e}")
            return False
    
    def record_agent_run(self, agent_id: str, input_data: Dict, output_data: Dict = None,
                        success: bool = True, error_message: str = None, 
                        execution_time: float = None) -> int:
        """
        Record an agent execution
        
        Args:
            agent_id: Agent identifier
            input_data: Input data for the run
            output_data: Output data from the run
            success: Whether the run was successful
            error_message: Error message if failed
            execution_time: Execution time in seconds
            
        Returns:
            Run ID if successful, -1 otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    INSERT INTO agent_runs 
                    (agent_id, input_data, output_data, success, error_message, execution_time, completed_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    agent_id,
                    json.dumps(input_data),
                    json.dumps(output_data) if output_data else None,
                    success,
                    error_message,
                    execution_time
                ))
                
                run_id = cursor.lastrowid
                
                # Update agent statistics
                if success:
                    conn.execute('''
                        UPDATE agents 
                        SET run_count = run_count + 1, 
                            success_count = success_count + 1,
                            last_run = CURRENT_TIMESTAMP,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE agent_id = ?
                    ''', (agent_id,))
                else:
                    conn.execute('''
                        UPDATE agents 
                        SET run_count = run_count + 1, 
                            error_count = error_count + 1,
                            last_run = CURRENT_TIMESTAMP,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE agent_id = ?
                    ''', (agent_id,))
                
                conn.commit()
                return run_id
        except Exception as e:
            print(f"Error recording agent run: {e}")
            return -1
    
    def get_agent_runs(self, agent_id: str, limit: int = 50) -> List[Dict]:
        """
        Get recent runs for an agent
        
        Args:
            agent_id: Agent identifier
            limit: Maximum number of runs to return
            
        Returns:
            List of run dictionaries
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute('''
                    SELECT * FROM agent_runs 
                    WHERE agent_id = ? 
                    ORDER BY started_at DESC 
                    LIMIT ?
                ''', (agent_id, limit))
                
                runs = []
                for row in cursor.fetchall():
                    run_data = dict(row)
                    # Parse JSON fields
                    if run_data['input_data']:
                        run_data['input_data'] = json.loads(run_data['input_data'])
                    if run_data['output_data']:
                        run_data['output_data'] = json.loads(run_data['output_data'])
                    runs.append(run_data)
                
                return runs
        except Exception as e:
            print(f"Error getting agent runs: {e}")
            return []
    
    def get_agent_stats(self, agent_id: str) -> Dict:
        """
        Get agent statistics
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Statistics dictionary
        """
        agent = self.get_agent(agent_id)
        if not agent:
            return {}
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get recent runs
                cursor = conn.execute('''
                    SELECT success, execution_time, started_at
                    FROM agent_runs 
                    WHERE agent_id = ? 
                    ORDER BY started_at DESC 
                    LIMIT 10
                ''', (agent_id,))
                
                recent_runs = cursor.fetchall()
                
                # Calculate additional stats
                total_runs = agent['run_count']
                success_rate = (agent['success_count'] / total_runs * 100) if total_runs > 0 else 0
                
                avg_execution_time = None
                if recent_runs:
                    execution_times = [run[1] for run in recent_runs if run[1] is not None]
                    if execution_times:
                        avg_execution_time = sum(execution_times) / len(execution_times)
                
                return {
                    'agent_id': agent_id,
                    'total_runs': total_runs,
                    'success_count': agent['success_count'],
                    'error_count': agent['error_count'],
                    'success_rate': round(success_rate, 2),
                    'last_run': agent['last_run'],
                    'avg_execution_time': round(avg_execution_time, 3) if avg_execution_time else None,
                    'status': agent['status'],
                    'deployed_at': agent['deployed_at'],
                    'framework': agent['framework']
                }
        except Exception as e:
            print(f"Error getting agent stats: {e}")
            return {}
    
    def cleanup_old_runs(self, days_old: int = 30) -> int:
        """
        Clean up old run records
        
        Args:
            days_old: Delete runs older than this many days
            
        Returns:
            Number of deleted records
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    DELETE FROM agent_runs 
                    WHERE started_at < datetime('now', '-{} days')
                '''.format(days_old))
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            print(f"Error cleaning up old runs: {e}")
            return 0
    
    def get_database_stats(self) -> Dict:
        """
        Get overall database statistics
        
        Returns:
            Database statistics dictionary
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get agent counts by status
                cursor = conn.execute('''
                    SELECT status, COUNT(*) as count 
                    FROM agents 
                    GROUP BY status
                ''')
                status_counts = dict(cursor.fetchall())
                
                # Get total runs
                cursor = conn.execute('SELECT COUNT(*) FROM agent_runs')
                total_runs = cursor.fetchone()[0]
                
                # Get database size
                db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
                
                return {
                    'total_agents': sum(status_counts.values()),
                    'agent_status_counts': status_counts,
                    'total_runs': total_runs,
                    'database_size_mb': round(db_size / 1024 / 1024, 2),
                    'database_path': str(self.db_path.absolute())
                }
        except Exception as e:
            print(f"Error getting database stats: {e}")
            return {}