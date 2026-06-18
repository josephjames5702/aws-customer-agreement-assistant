import json
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.query_log import QueryLog
from typing import Dict, Any, List

class DBLogger:
    """Handles insertions into and metrics retrieval from the query logs database."""

    @staticmethod
    def log_query(
        db: Session,
        query: str,
        answer: str,
        answer_found: bool,
        response_time_ms: float,
        sources: List[Dict[str, Any]],
        model_used: str
    ) -> QueryLog:
        """Logs a single query-answer interaction to SQL."""
        log_entry = QueryLog(
            query=query,
            answer=answer,
            answer_found=answer_found,
            response_time_ms=response_time_ms,
            source_chunks=json.dumps(sources),  # Convert list of sources to JSON string
            created_at=func.now()  # Use DB server time
        )
        db.add(log_entry)
        db.commit()
        db.refresh(log_entry)
        return log_entry

    @staticmethod
    def get_analytics(db: Session) -> Dict[str, Any]:
        """Calculates aggregated metrics from the query logs table."""
        # 1. Total queries
        total = db.query(QueryLog).count()
        if total == 0:
            return {
                "total_queries": 0,
                "average_response_time_ms": 0.0,
                "unanswered_queries": [],
                "top_5_questions": [],
                "answer_found_rate_pct": 0.0,
                "min_latency_ms": 0.0,
                "max_latency_ms": 0.0,
                "top_queries": [],
                "unanswerable_queries": [],
                "query_volume_by_hour": []
            }

        # 2. Latency stats
        latency_stats = db.query(
            func.avg(QueryLog.response_time_ms),
            func.min(QueryLog.response_time_ms),
            func.max(QueryLog.response_time_ms)
        ).first()
        
        avg_latency = float(latency_stats[0]) if latency_stats[0] is not None else 0.0
        min_latency = float(latency_stats[1]) if latency_stats[1] is not None else 0.0
        max_latency = float(latency_stats[2]) if latency_stats[2] is not None else 0.0

        # 3. Answer found rate
        answered_count = db.query(QueryLog).filter(QueryLog.answer_found == True).count()
        found_rate = round((answered_count / total) * 100.0, 2)

        # 4. Unanswered/Unanswerable queries (where answer_found = False)
        unanswered = db.query(QueryLog.query, QueryLog.created_at).filter(
            QueryLog.answer_found == False
        ).order_by(QueryLog.created_at.desc()).limit(20).all()
        
        unanswered_list = [
            {"query": q[0], "created_at": q[1]}
            for q in unanswered
        ]

        # 5. Top questions (grouped by identical or similar queries)
        top_q = db.query(QueryLog.query, func.count(QueryLog.id).label("count")).group_by(
            QueryLog.query
        ).order_by(func.count(QueryLog.id).desc()).limit(10).all()
        
        top_list = [
            {"query": q[0], "frequency": q[1]}
            for q in top_q
        ]

        # 6. Hourly volume
        # We group by hour of created_at using SQLite strftime or generic parsing
        # For cross-DB compatibility, we fetch raw dates and aggregate in Python
        all_dates = db.query(QueryLog.created_at).all()
        hourly_counts = {}
        for row in all_dates:
            dt = row[0]
            if dt:
                hour = f"{dt.hour:02d}"
                hourly_counts[hour] = hourly_counts.get(hour, 0) + 1
        
        query_volume_by_hour = [
            {"hour": hr, "queries": count}
            for hr, count in sorted(hourly_counts.items())
        ]

        return {
            "total_queries": total,
            "average_response_time_ms": round(avg_latency, 2),
            "unanswered_queries": unanswered_list,
            "top_5_questions": top_list[:5],
            
            # Compatibility with PRD specs
            "answer_found_rate_pct": found_rate,
            "min_latency_ms": round(min_latency, 2),
            "max_latency_ms": round(max_latency, 2),
            "top_queries": top_list,
            "unanswerable_queries": unanswered_list,
            "query_volume_by_hour": query_volume_by_hour
        }
