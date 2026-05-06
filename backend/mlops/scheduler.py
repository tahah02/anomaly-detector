import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from backend.mlops.retraining_pipeline import run_retraining
from backend.db_service import get_db_service

logger = logging.getLogger(__name__)

_scheduler = None
_current_interval = None


class MLOpsScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.is_running = False
    
    def add_weekly_job(self, day_of_week: int = 0, hour: int = 2, minute: int = 0):
        try:
            self.scheduler.add_job(
                func=run_retraining,
                trigger=CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute),
                id='weekly_retraining',
                name='Weekly Model Retraining',
                replace_existing=True
            )
            logger.info(f"Added weekly retraining job: {day_of_week} {hour}:{minute:02d}")
        except Exception as e:
            logger.error(f"Error adding weekly job: {e}")
    
    def add_monthly_job(self, day: int = 1, hour: int = 3, minute: int = 0):
        try:
            self.scheduler.add_job(
                func=run_retraining,
                trigger=CronTrigger(day=day, hour=hour, minute=minute),
                id='monthly_retraining',
                name='Monthly Model Retraining',
                replace_existing=True
            )
            logger.info(f"Added monthly retraining job: day {day} {hour}:{minute:02d}")
        except Exception as e:
            logger.error(f"Error adding monthly job: {e}")
    
    def add_interval_job(self, interval: str):
        try:
            if interval == '1H':
                trigger = IntervalTrigger(hours=1)
            elif interval == '1D':
                trigger = IntervalTrigger(days=1)
            elif interval == '1W':
                trigger = IntervalTrigger(weeks=1)
            elif interval == '1M':
                trigger = IntervalTrigger(days=30)
            elif interval == '1Y':
                trigger = IntervalTrigger(days=365)
            else:
                raise ValueError(f"Invalid interval: {interval}")
            
            self.scheduler.add_job(
                func=run_retraining,
                trigger=trigger,
                id='interval_retraining',
                name=f'Interval Retraining ({interval})',
                replace_existing=True
            )
            logger.info(f"Added interval retraining job: {interval}")
        except Exception as e:
            logger.error(f"Error adding interval job: {e}")
    
    def add_custom_job(self, job_id: str, cron_expression: str):
        try:
            parts = cron_expression.split()
            if len(parts) != 5:
                raise ValueError("Invalid cron expression format")
            
            self.scheduler.add_job(
                func=run_retraining,
                trigger=CronTrigger(minute=parts[0], hour=parts[1], day=parts[2], month=parts[3], day_of_week=parts[4]),
                id=job_id,
                name=f'Custom Retraining Job: {job_id}',
                replace_existing=True
            )
            logger.info(f"Added custom job '{job_id}': {cron_expression}")
        except Exception as e:
            logger.error(f"Error adding custom job: {e}")
    
    def start(self):
        try:
            if not self.is_running:
                self.scheduler.start()
                self.is_running = True
                logger.info("MLOps Scheduler started")
            else:
                logger.warning("Scheduler already running")
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")
    
    def stop(self):
        try:
            if self.is_running:
                self.scheduler.shutdown()
                self.is_running = False
                logger.info("MLOps Scheduler stopped")
            else:
                logger.warning("Scheduler not running")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
    
    def get_jobs(self):
        return self.scheduler.get_jobs()
    
    def remove_job(self, job_id: str):
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed job: {job_id}")
        except Exception as e:
            logger.error(f"Error removing job: {e}")


def check_and_update_schedule():
    try:
        global _current_interval
        db = get_db_service()
        
        query = "SELECT Interval, IsEnabled FROM RetrainingConfig WHERE ConfigId = 1"
        result = db.execute_query(query)
        
        if result is not None and not result.empty:
            interval = result['Interval'].values[0]
            is_enabled = result['IsEnabled'].values[0]
            
            if is_enabled and interval != _current_interval:
                logger.info(f"Interval changed from {_current_interval} to {interval}")
                _current_interval = interval
                
                scheduler = get_scheduler()
                scheduler.add_interval_job(interval)
                
                query_update = "UPDATE RetrainingConfig SET UpdatedAt = GETDATE() WHERE ConfigId = 1"
                db.execute_non_query(query_update)
        
    except Exception as e:
        logger.error(f"Error checking schedule config: {e}")


def get_scheduler() -> MLOpsScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = MLOpsScheduler()
    return _scheduler


def start_scheduler():
    scheduler = get_scheduler()
    
    # Read scheduler times from database
    try:
        db = get_db_service()
        query = """
            SELECT WeeklyJobDay, WeeklyJobHour, WeeklyJobMinute, 
                   MonthlyJobDay, MonthlyJobHour, MonthlyJobMinute 
            FROM RetrainingConfig WHERE ConfigId = 1
        """
        result = db.execute_query(query)
        
        if result is not None and not result.empty:
            weekly_day = int(result['WeeklyJobDay'].values[0])
            weekly_hour = int(result['WeeklyJobHour'].values[0])
            weekly_minute = int(result['WeeklyJobMinute'].values[0])
            
            monthly_day = int(result['MonthlyJobDay'].values[0])
            monthly_hour = int(result['MonthlyJobHour'].values[0])
            monthly_minute = int(result['MonthlyJobMinute'].values[0])
        else:
            # Fallback to defaults if query fails
            weekly_day, weekly_hour, weekly_minute = 0, 2, 0
            monthly_day, monthly_hour, monthly_minute = 1, 3, 0
            logger.warning("Could not read scheduler config from database, using defaults")
    except Exception as e:
        logger.error(f"Error reading scheduler config from database: {e}")
        # Fallback to defaults
        weekly_day, weekly_hour, weekly_minute = 0, 2, 0
        monthly_day, monthly_hour, monthly_minute = 1, 3, 0
    
    scheduler.scheduler.add_job(
        func=check_and_update_schedule,
        trigger="interval",
        minutes=5,
        id='config_checker'
    )
    
    scheduler.add_weekly_job(day_of_week=weekly_day, hour=weekly_hour, minute=weekly_minute)
    scheduler.add_monthly_job(day=monthly_day, hour=monthly_hour, minute=monthly_minute)
    
    scheduler.start()


def stop_scheduler():
    scheduler = get_scheduler()
    scheduler.stop()
