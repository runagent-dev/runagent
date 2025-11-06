"""
RunAgent Wrapper for StockAgent - RUNS REAL SIMULATION WITH FULL LOGGING
"""
import json
import time
import sys
import io
import logging
from typing import Dict, Any, Iterator
from dataclasses import dataclass, asdict
import os
import random
from contextlib import redirect_stdout, redirect_stderr

# Import StockAgent modules
from main import handle_action
from agent import Agent
from stock import Stock
import util


@dataclass
class SimulationUpdate:
    """Structure for simulation updates"""
    type: str
    day: int
    session: int = 0
    message: str = ""
    data: Dict[str, Any] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.data is None:
            self.data = {}


class LogCapture:
    """Captures all log output and yields it"""
    def __init__(self):
        self.buffer = io.StringIO()
        self.logs = []
        
    def write(self, text):
        if text and text.strip():
            self.logs.append(text)
        self.buffer.write(text)
        
    def flush(self):
        self.buffer.flush()
        
    def get_logs(self):
        """Get and clear accumulated logs"""
        logs = self.logs.copy()
        self.logs.clear()
        return logs


class StockAgentRunner:
    """Wrapper class to run StockAgent simulations"""
    
    def __init__(self):
        self.simulation_state = {
            "status": "ready",
            "current_day": 0,
            "total_days": 0,
            "agents": [],
            "stocks": {},
            "events": []
        }
    
    def stream_simulation(
        self,
        num_agents: int = 10,
        total_days: int = 30,
        sessions_per_day: int = 3,
        model: str = "gpt-4o-mini",
        stock_a_price: float = 30.0,
        stock_b_price: float = 40.0,
        enable_events: bool = True
    ) -> Iterator[Dict[str, Any]]:
        """Stream REAL simulation with LLM agents and ALL logs"""
        
        # FIX: Convert string parameters to appropriate types
        try:
            num_agents = int(num_agents) if isinstance(num_agents, str) else num_agents
            total_days = int(total_days) if isinstance(total_days, str) else total_days
            sessions_per_day = int(sessions_per_day) if isinstance(sessions_per_day, str) else sessions_per_day
            stock_a_price = float(stock_a_price) if isinstance(stock_a_price, str) else stock_a_price
            stock_b_price = float(stock_b_price) if isinstance(stock_b_price, str) else stock_b_price
            
            # Convert string boolean to actual boolean
            if isinstance(enable_events, str):
                enable_events = enable_events.lower() in ('true', '1', 'yes', 'on')
        except (ValueError, TypeError) as e:
            yield asdict(SimulationUpdate(
                type="error",
                day=0,
                message=f"❌ Parameter conversion error: {str(e)}",
                data={"error": str(e)}
            ))
            return
        
        # Setup log capturing
        log_capture = LogCapture()
        
        # Get the StockAgent logger and add our handler
        from log.custom_logger import log as stock_logger
        capture_handler = logging.StreamHandler(log_capture)
        capture_handler.setLevel(logging.DEBUG)
        stock_logger.logger.addHandler(capture_handler)
        
        try:
            yield asdict(SimulationUpdate(
                type="init",
                day=0,
                message="🚀 Initializing REAL StockAgent simulation...",
                data={
                    "num_agents": num_agents,
                    "total_days": total_days,
                    "sessions_per_day": sessions_per_day,
                    "model": model
                }
            ))
            
            # Update util settings with converted values
            util.AGENTS_NUM = num_agents
            util.TOTAL_DATE = total_days
            util.TOTAL_SESSION = sessions_per_day
            util.STOCK_A_INITIAL_PRICE = stock_a_price
            util.STOCK_B_INITIAL_PRICE = stock_b_price
            
            if not enable_events:
                util.EVENT_1_DAY = total_days + 1
                util.EVENT_2_DAY = total_days + 2
            
            # Run REAL simulation with log streaming
            for update in self._run_real_simulation_streaming(model, log_capture):
                yield asdict(update)
            
            yield asdict(SimulationUpdate(
                type="complete",
                day=total_days,
                message="🎉 Real simulation completed!",
                data=self._collect_results()
            ))
            
        except Exception as e:
            import traceback
            yield asdict(SimulationUpdate(
                type="error",
                day=0,
                message=f"❌ Error: {str(e)}",
                data={"error": str(e), "traceback": traceback.format_exc()}
            ))
        finally:
            # Remove our handler
            stock_logger.logger.removeHandler(capture_handler)
    
    def _run_real_simulation_streaming(self, model: str, log_capture: LogCapture) -> Iterator[SimulationUpdate]:
        """REAL simulation with actual LLM calls and log streaming"""
        from secretary import Secretary
        from log.custom_logger import log
        from record import create_stock_record
        
        secretary = Secretary(model)
        stock_a = Stock("A", util.STOCK_A_INITIAL_PRICE, 0, is_new=False)
        stock_b = Stock("B", util.STOCK_B_INITIAL_PRICE, 0, is_new=False)
        
        all_agents = []
        log.logger.info("🤖 Initializing LLM agents...")
        
        # Yield any logs from initialization
        for log_line in log_capture.get_logs():
            yield SimulationUpdate(
                type="log",
                day=0,
                message=log_line.strip()
            )
        
        for i in range(util.AGENTS_NUM):
            agent = Agent(i, stock_a.get_price(), stock_b.get_price(), secretary, model)
            all_agents.append(agent)
            
            # Yield logs after each agent creation
            for log_line in log_capture.get_logs():
                yield SimulationUpdate(
                    type="log",
                    day=0,
                    message=log_line.strip()
                )
        
        yield SimulationUpdate(
            type="agents_initialized",
            day=0,
            message=f"✅ Initialized {len(all_agents)} REAL LLM agents",
            data={"num_agents": len(all_agents)}
        )
        
        last_day_forum_message = []
        stock_a_deals = {"sell": [], "buy": []}
        stock_b_deals = {"sell": [], "buy": []}
        
        for date in range(1, util.TOTAL_DATE + 1):
            stock_a_deals["sell"].clear()
            stock_a_deals["buy"].clear()
            stock_b_deals["buy"].clear()
            stock_b_deals["sell"].clear()
            
            for agent in all_agents[:]:
                agent.chat_history.clear()
                agent.loan_repayment(date)
                
                # Yield logs
                for log_line in log_capture.get_logs():
                    yield SimulationUpdate(
                        type="log",
                        day=date,
                        message=log_line.strip()
                    )
            
            if date in util.REPAYMENT_DAYS:
                for agent in all_agents[:]:
                    agent.interest_payment()
                    
                    # Yield logs
                    for log_line in log_capture.get_logs():
                        yield SimulationUpdate(
                            type="log",
                            day=date,
                            message=log_line.strip()
                        )
            
            for agent in all_agents[:]:
                if agent.is_bankrupt:
                    quit_sig = agent.bankrupt_process(stock_a.get_price(), stock_b.get_price())
                    if quit_sig:
                        agent.quit = True
                        all_agents.remove(agent)
                    
                    # Yield logs
                    for log_line in log_capture.get_logs():
                        yield SimulationUpdate(
                            type="log",
                            day=date,
                            message=log_line.strip()
                        )
            
            if date == util.EVENT_1_DAY:
                util.LOAN_RATE = util.EVENT_1_LOAN_RATE
                last_day_forum_message.append({"name": -1, "message": util.EVENT_1_MESSAGE})
            
            if date == util.EVENT_2_DAY:
                util.LOAN_RATE = util.EVENT_2_LOAN_RATE
                last_day_forum_message.append({"name": -1, "message": util.EVENT_2_MESSAGE})
            
            yield SimulationUpdate(
                type="day_start",
                day=date,
                message=f"📅 Day {date}/{util.TOTAL_DATE}",
                data={
                    "stock_a_price": stock_a.get_price(),
                    "stock_b_price": stock_b.get_price(),
                    "active_agents": len(all_agents)
                }
            )
            
            # REAL LLM CALLS FOR LOANS
            for agent in all_agents:
                loan = agent.plan_loan(date, stock_a.get_price(), stock_b.get_price(), last_day_forum_message)
                
                # Yield logs after each loan decision
                for log_line in log_capture.get_logs():
                    yield SimulationUpdate(
                        type="log",
                        day=date,
                        message=log_line.strip()
                    )
            
            for session in range(1, util.TOTAL_SESSION + 1):
                trades_count = 0
                sequence = list(range(len(all_agents)))
                random.shuffle(sequence)
                
                # REAL LLM CALLS FOR TRADING
                for i in sequence:
                    agent = all_agents[i]
                    action = agent.plan_stock(date, session, stock_a, stock_b, stock_a_deals, stock_b_deals)
                    
                    # Yield logs after each trading decision
                    for log_line in log_capture.get_logs():
                        yield SimulationUpdate(
                            type="log",
                            day=date,
                            session=session,
                            message=log_line.strip()
                        )
                    
                    if action.get("action_type") != "no":
                        trades_count += 1
                        action["agent"] = agent.order
                        action["date"] = date
                        
                        if action["stock"] == 'A':
                            handle_action(action, stock_a_deals, all_agents, stock_a, session)
                        else:
                            handle_action(action, stock_b_deals, all_agents, stock_b, session)
                        
                        # Yield logs after action handling
                        for log_line in log_capture.get_logs():
                            yield SimulationUpdate(
                                type="log",
                                day=date,
                                session=session,
                                message=log_line.strip()
                            )
                
                stock_a.update_price(date)
                stock_b.update_price(date)
                create_stock_record(date, session, stock_a.get_price(), stock_b.get_price())
                
                yield SimulationUpdate(
                    type="session",
                    day=date,
                    session=session,
                    message=f"⏰ Session {session} - {trades_count} trades",
                    data={
                        "stock_a_price": stock_a.get_price(),
                        "stock_b_price": stock_b.get_price(),
                        "trades": trades_count
                    }
                )
                
                # Yield any remaining logs from session
                for log_line in log_capture.get_logs():
                    yield SimulationUpdate(
                        type="log",
                        day=date,
                        session=session,
                        message=log_line.strip()
                    )
            
            # REAL LLM CALLS FOR FORUM POSTS
            last_day_forum_message.clear()
            for agent in all_agents:
                message = agent.post_message()
                last_day_forum_message.append({"name": agent.order, "message": message})
                
                # Yield logs after each forum post
                for log_line in log_capture.get_logs():
                    yield SimulationUpdate(
                        type="log",
                        day=date,
                        message=log_line.strip()
                    )
            
            yield SimulationUpdate(
                type="day_end",
                day=date,
                message=f"✅ Day {date} done",
                data={
                    "stock_a_price": stock_a.get_price(),
                    "stock_b_price": stock_b.get_price(),
                    "surviving_agents": len(all_agents)
                }
            )

    
    def _collect_results(self) -> Dict[str, Any]:
        results = {"trades": [], "stock_prices": [], "agent_performance": []}
        try:
            import pandas as pd
            if os.path.exists("res/trades.xlsx"):
                results["trades"] = pd.read_excel("res/trades.xlsx").to_dict('records')
            if os.path.exists("res/stocks.xlsx"):
                results["stock_prices"] = pd.read_excel("res/stocks.xlsx").to_dict('records')
        except: pass
        return results


runner = StockAgentRunner()


def stream_simulation(**kwargs) -> Iterator[Dict[str, Any]]:
    """Streaming simulation - yields updates AND logs in real-time"""
    for update in runner.stream_simulation(**kwargs):
        yield update


def get_simulation_status() -> Dict[str, Any]:
    """Get current simulation status"""
    return runner.simulation_state