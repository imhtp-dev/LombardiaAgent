"""
Dashboard statistics endpoints (from Pipecat call data)
All data comes from PostgreSQL tables: tb_stat, tb_voice_agent, pipecat_sessions
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from loguru import logger

from .database import db
from .models import (
    DashboardStats,
    CallListResponse,
    CallSummaryResponse,
    RegionItem,
    VoiceAgent,
    AdditionalStatsResponse,
    PatientIntentStatsResponse,
    CallOutcomeStatsResponse,
    MotivationAnalysisResponse,
    ClinicalKPIsResponse,
    TrendResponse,
    MotivationsByOutcomeResponse
)


router = APIRouter()


# ==================== Helper Functions ====================

async def get_assistant_id_by_region(region: str) -> Optional[str]:
    """
    Get assistant_id for a specific region
    
    Args:
        region: Region name or "All Region"
    
    Returns:
        Assistant ID or None for "All Region"
    """
    try:
        if region == "All Region":
            return None
        
        query = """
        SELECT assistant_id
        FROM tb_voice_agent
        WHERE regione = $1
        LIMIT 1
        """
        
        result = await db.fetchrow(query, region)
        
        if result:
            logger.info(f"✅ Found assistant_id {result['assistant_id']} for region {region}")
            return result['assistant_id']
        else:
            logger.warning(f"⚠️ No assistant_id found for region {region}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Error getting assistant_id for region {region}: {e}")
        return None


# ==================== Dashboard Endpoints ====================

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    region: str = "All Region",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    Get main dashboard statistics
    
    Args:
        region: Region name or "All Region"
        start_date: Start date filter (YYYY-MM-DD)
        end_date: End date filter (YYYY-MM-DD)
    
    Returns:
        Dashboard statistics
    """
    try:
        logger.info(f"📊 Loading dashboard data for region: {region}")
        if start_date and end_date:
            logger.info(f"📅 Date filter: {start_date} to {end_date}")
        
        # Get assistant_id for region
        assistant_id = await get_assistant_id_by_region(region)
        
        # Build WHERE clause
        base_where = "WHERE started_at IS NOT NULL"
        params = []
        param_count = 1
        
        if assistant_id:
            base_where += f" AND assistant_id = ${param_count}"
            params.append(assistant_id)
            param_count += 1
        
        # Add date filter if provided
        if start_date and end_date:
            base_where += f" AND DATE(started_at) >= ${param_count} AND DATE(started_at) <= ${param_count + 1}"
            params.extend([start_date, end_date])
            param_count += 2
        
        # Query for total stats
        total_stats_query = f"""
        SELECT
            COUNT(*) as total_calls,
            COALESCE(SUM(duration_seconds), 0) as total_duration_seconds,
            COALESCE(AVG(duration_seconds), 0) as avg_duration_seconds
        FROM tb_stat
        {base_where}
        """
        
        total_stats = await db.fetchrow(total_stats_query, *params)
        
        # Calculate totals
        total_calls = total_stats['total_calls'] if total_stats else 0
        total_duration_seconds = total_stats['total_duration_seconds'] if total_stats else 0
        avg_duration_seconds = total_stats['avg_duration_seconds'] if total_stats else 0
        
        # Convert to minutes
        total_minutes = int(total_duration_seconds / 60) if total_duration_seconds else 0
        avg_duration_minutes = round(avg_duration_seconds / 60, 1) if avg_duration_seconds else 0.0
        
        # Calculate revenue (0.006 euro per second)
        total_revenue = round(total_duration_seconds * 0.006, 2) if total_duration_seconds else 0.0
        
        # Query for chart data (last 7 days or date range)
        if start_date and end_date:
            chart_where = f"WHERE DATE(started_at) >= ${param_count} AND DATE(started_at) <= ${param_count + 1} AND started_at IS NOT NULL"
            chart_params = [start_date, end_date]
            param_count_chart = param_count + 2
        else:
            chart_where = "WHERE started_at >= CURRENT_DATE - INTERVAL '6 days' AND started_at IS NOT NULL"
            chart_params = []
            param_count_chart = 1
        
        if assistant_id:
            chart_where += f" AND assistant_id = ${param_count_chart}"
            chart_params.append(assistant_id)
        
        chart_query = f"""
        SELECT
            DATE(started_at) as call_date,
            COUNT(*) as daily_calls,
            COALESCE(SUM(duration_seconds), 0) as daily_duration_seconds
        FROM tb_stat
        {chart_where}
        GROUP BY DATE(started_at)
        ORDER BY call_date ASC
        """
        
        chart_data_result = await db.fetch(chart_query, *chart_params)
        
        # Prepare chart data
        chart_data = []
        
        if start_date and end_date:
            # Generate all days in range
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            
            current_date = start_dt
            while current_date <= end_dt:
                date_str = current_date.strftime("%Y-%m-%d")
                
                # Find data for this date
                day_data = next((row for row in chart_data_result if str(row['call_date']) == date_str), None)
                
                if day_data:
                    daily_calls = day_data['daily_calls']
                    daily_duration_seconds = day_data['daily_duration_seconds']
                    daily_minutes = int(daily_duration_seconds / 60) if daily_duration_seconds else 0
                    daily_revenue = round(daily_duration_seconds * 0.006, 2) if daily_duration_seconds else 0.0
                else:
                    daily_calls = 0
                    daily_minutes = 0
                    daily_revenue = 0.0
                
                chart_data.append({
                    "date": date_str,
                    "calls": daily_calls,
                    "minutes": daily_minutes,
                    "revenue": daily_revenue
                })
                
                current_date += timedelta(days=1)
        else:
            # Last 7 days
            for i in range(7):
                date = datetime.now().date() - timedelta(days=6-i)
                date_str = date.strftime("%Y-%m-%d")
                
                day_data = next((row for row in chart_data_result if str(row['call_date']) == date_str), None)
                
                if day_data:
                    daily_calls = day_data['daily_calls']
                    daily_duration_seconds = day_data['daily_duration_seconds']
                    daily_minutes = int(daily_duration_seconds / 60) if daily_duration_seconds else 0
                    daily_revenue = round(daily_duration_seconds * 0.006, 2) if daily_duration_seconds else 0.0
                else:
                    daily_calls = 0
                    daily_minutes = 0
                    daily_revenue = 0.0
                
                chart_data.append({
                    "date": date_str,
                    "calls": daily_calls,
                    "minutes": daily_minutes,
                    "revenue": daily_revenue
                })
        
        logger.info(f"✅ Dashboard data loaded: {total_calls} calls, {total_minutes} minutes, €{total_revenue}")
        
        return DashboardStats(
            total_minutes=total_minutes,
            total_revenue=total_revenue,
            total_calls=total_calls,
            chart_data=chart_data,
            avg_duration_minutes=avg_duration_minutes
        )
        
    except Exception as e:
        logger.error(f"❌ Error loading dashboard data: {e}")
        import traceback
        traceback.print_exc()
        # Return empty data on error
        return DashboardStats(
            total_minutes=0,
            total_revenue=0.0,
            total_calls=0,
            chart_data=[],
            avg_duration_minutes=0.0
        )


@router.get("/calls", response_model=CallListResponse)
async def get_calls(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    region: str = "All Region",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    Get paginated list of calls
    
    Args:
        limit: Maximum number of calls to return
        offset: Offset for pagination
        region: Region filter
        start_date: Start date filter
        end_date: End date filter
    
    Returns:
        Paginated call list
    """
    try:
        logger.info(f"📋 Loading calls (limit: {limit}, offset: {offset}, region: {region})")
        
        # Get assistant_id for region
        assistant_id = await get_assistant_id_by_region(region)
        
        # Build WHERE clause
        base_where = "WHERE started_at IS NOT NULL"
        params = []
        param_count = 1
        
        if assistant_id:
            base_where += f" AND assistant_id = ${param_count}"
            params.append(assistant_id)
            param_count += 1
        
        # Add date filter
        if start_date and end_date:
            base_where += f" AND DATE(started_at) >= ${param_count} AND DATE(started_at) <= ${param_count + 1}"
            params.extend([start_date, end_date])
            param_count += 2
        
        # Count total
        count_query = f"SELECT COUNT(*) as total FROM tb_stat {base_where}"
        count_result = await db.fetchrow(count_query, *params)
        total_calls = count_result['total'] if count_result else 0
        
        # Get paginated data
        data_query = f"""
        SELECT
            id_stat as id,
            started_at,
            call_id,
            interaction_id,
            phone_number,
            duration_seconds,
            action,
            sentiment,
            motivazione,
            esito_chiamata
        FROM tb_stat
        {base_where}
        ORDER BY started_at DESC
        LIMIT ${param_count} OFFSET ${param_count + 1}
        """
        
        params.extend([limit, offset])
        results = await db.fetch(data_query, *params)
        
        calls = []
        for row in results:
            calls.append({
                "id": row['id'],
                "started_at": row['started_at'].isoformat() if row['started_at'] else None,
                "call_id": row['call_id'],
                "interaction_id": row['interaction_id'],
                "phone_number": row['phone_number'],
                "duration_seconds": int(row['duration_seconds']) if row['duration_seconds'] else 0,
                "action": row['action'] if row['action'] else "N/A",
                "sentiment": row['sentiment'] if row['sentiment'] else "N/A",
                "motivazione": row['motivazione'] if row['motivazione'] else "N/A",
                "esito_chiamata": row['esito_chiamata'] if row['esito_chiamata'] else "N/A"
            })
        
        # Calculate pagination info
        total_pages = (total_calls + limit - 1) // limit
        current_page = (offset // limit) + 1
        has_next = offset + limit < total_calls
        has_previous = offset > 0
        
        result = {
            "calls": calls,
            "pagination": {
                "total_calls": total_calls,
                "total_pages": total_pages,
                "current_page": current_page,
                "has_next": has_next,
                "has_previous": has_previous,
                "limit": limit,
                "offset": offset
            }
        }
        
        logger.info(f"✅ Loaded {len(calls)} calls (page {current_page}/{total_pages})")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error loading calls: {e}")
        return {
            "calls": [],
            "pagination": {
                "total_calls": 0,
                "total_pages": 0,
                "current_page": 1,
                "has_next": False,
                "has_previous": False,
                "limit": limit,
                "offset": offset
            }
        }


@router.get("/call/{call_id}/summary", response_model=CallSummaryResponse)
async def get_call_summary(call_id: str):
    """
    Get call summary and details from Pipecat data
    
    Args:
        call_id: Call ID
    
    Returns:
        Call summary with transcript and metadata
    """
    try:
        logger.info(f"📞 Getting summary for call: {call_id}")
        
        # Query tb_stat for call data
        query = """
        SELECT
            call_id,
            started_at,
            ended_at,
            patient_intent,
            esito_chiamata,
            motivazione
        FROM tb_stat
        WHERE call_id = $1
        LIMIT 1
        """
        
        call_data = await db.fetchrow(query, call_id)
        
        if not call_data:
            raise HTTPException(status_code=404, detail="Chiamata non trovata")
        
        # For now, return basic data (transcript/summary from pipecat_sessions can be added later)
        return CallSummaryResponse(
            success=True,
            call_id=call_id,
            summary=call_data['motivazione'] or "Nessun summary disponibile",
            transcript="Transcript non ancora implementato",  # TODO: Get from pipecat_sessions
            started_at=call_data['started_at'].isoformat() if call_data['started_at'] else None,
            ended_at=call_data['ended_at'].isoformat() if call_data['ended_at'] else None,
            patient_intent=call_data['patient_intent'],
            esito_chiamata=call_data['esito_chiamata'],
            motivazione=call_data['motivazione'],
            has_analysis=bool(call_data['patient_intent']),
            has_transcript=False  # TODO: Check pipecat_sessions
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting call summary: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore nel recupero del summary: {str(e)}"
        )


@router.get("/regions", response_model=List[RegionItem])
async def get_regions():
    """
    Get list of all available regions
    
    Returns:
        List of regions
    """
    try:
        logger.info("🌍 Getting available regions")
        
        query = """
        SELECT DISTINCT regione
        FROM tb_voice_agent
        WHERE regione IS NOT NULL
        ORDER BY regione ASC
        """
        
        results = await db.fetch(query)
        
        # Build regions list with "All Region" first
        regions = [{"value": "All Region", "label": "All Region"}]
        
        for row in results:
            if row['regione']:
                regions.append({
                    "value": row['regione'],
                    "label": row['regione']
                })
        
        logger.info(f"✅ Found {len(regions)-1} unique regions + All Region")
        return regions
        
    except Exception as e:
        logger.error(f"❌ Error getting regions: {e}")
        return [{"value": "All Region", "label": "All Region"}]


@router.get("/voice-agents", response_model=List[VoiceAgent])
async def get_voice_agents():
    """
    Get list of all voice agents
    
    Returns:
        List of voice agents
    """
    try:
        logger.info("🎤 Getting voice agents")
        
        query = """
        SELECT id_voice_agent, regione, assistant_id
        FROM tb_voice_agent
        WHERE public = true
        ORDER BY regione ASC
        """
        
        results = await db.fetch(query)
        
        voice_agents = [VoiceAgent(**row) for row in results]
        
        logger.info(f"✅ Found {len(voice_agents)} voice agents")
        return voice_agents
        
    except Exception as e:
        logger.error(f"❌ Error fetching voice agents: {e}")
        return []


@router.get("/additional-stats", response_model=AdditionalStatsResponse)
async def get_additional_stats(
    region: str = "All Region",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    Get additional dashboard statistics
    
    Args:
        region: Region filter
        start_date: Start date filter
        end_date: End date filter
    
    Returns:
        Additional statistics (sentiment, action, hourly)
    """
    try:
        logger.info(f"📈 Loading additional stats for region: {region}")
        
        assistant_id = await get_assistant_id_by_region(region)
        
        # Build base WHERE clause
        if start_date and end_date:
            base_where = "WHERE sentiment IS NOT NULL AND DATE(started_at) >= $1 AND DATE(started_at) <= $2"
            base_params = [start_date, end_date]
            param_count = 3
        else:
            base_where = "WHERE sentiment IS NOT NULL AND started_at >= NOW() - INTERVAL '27 days'"
            base_params = []
            param_count = 1
        
        if assistant_id:
            base_where += f" AND assistant_id = ${param_count}"
            base_params.append(assistant_id)
        
        # Sentiment stats
        sentiment_query = f"""
        SELECT sentiment, COUNT(*) as count
        FROM tb_stat
        {base_where}
        GROUP BY sentiment
        """
        sentiment_stats = await db.fetch(sentiment_query, *base_params)
        
        # Action stats
        action_base = base_where.replace("sentiment IS NOT NULL", "action IS NOT NULL")
        action_query = f"""
        SELECT
            action,
            COUNT(*) as count,
            AVG(duration_seconds) as avg_duration
        FROM tb_stat
        {action_base}
        GROUP BY action
        """
        action_stats = await db.fetch(action_query, *base_params)
        
        # Hourly stats
        hourly_base = base_where.replace("sentiment IS NOT NULL", "started_at IS NOT NULL")
        hourly_query = f"""
        SELECT
            EXTRACT(HOUR FROM started_at) as hour,
            COUNT(*) as calls_count
        FROM tb_stat
        {hourly_base}
        GROUP BY EXTRACT(HOUR FROM started_at)
        ORDER BY hour
        """
        hourly_stats = await db.fetch(hourly_query, *base_params)
        
        return AdditionalStatsResponse(
            sentiment_stats=[dict(row) for row in sentiment_stats],
            action_stats=[dict(row) for row in action_stats],
            hourly_stats=[dict(row) for row in hourly_stats]
        )
        
    except Exception as e:
        logger.error(f"❌ Error loading additional stats: {e}")
        return AdditionalStatsResponse(
            sentiment_stats=[],
            action_stats=[],
            hourly_stats=[]
        )


@router.get("/patient-intent-stats", response_model=PatientIntentStatsResponse)
async def get_patient_intent_stats(
    region: str = "All Region",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    Get patient intent statistics
    
    Returns:
        Patient intent statistics
    """
    try:
        logger.info(f"🎯 Patient intent stats for region: {region}")
        
        assistant_id = await get_assistant_id_by_region(region)
        
        base_where = "WHERE patient_intent IS NOT NULL AND patient_intent != '' AND patient_intent != 'NULL'"
        params = []
        param_count = 1
        
        if assistant_id:
            base_where += f" AND assistant_id = ${param_count}"
            params.append(assistant_id)
            param_count += 1
        
        if start_date and end_date:
            # Ensure not before 2024-09-26
            actual_start = max(start_date, "2024-09-26") if start_date < "2024-09-26" else start_date
            base_where += f" AND DATE(started_at) >= ${param_count} AND DATE(started_at) <= ${param_count + 1}"
            params.extend([actual_start, end_date])
        
        query = f"""
        SELECT patient_intent, COUNT(*) as count
        FROM tb_stat
        {base_where}
        GROUP BY patient_intent
        ORDER BY count DESC
        LIMIT 20
        """
        
        result = await db.fetch(query, *params)
        
        # Get total
        total_query = f"SELECT COUNT(*) as total FROM tb_stat {base_where}"
        total_result = await db.fetchrow(total_query, *params)
        total_calls = total_result['total'] if total_result else 0
        
        return PatientIntentStatsResponse(
            patient_intent_stats=[dict(row) for row in result],
            total_calls_with_intent=total_calls
        )
        
    except Exception as e:
        logger.error(f"❌ Error in patient intent stats: {e}")
        return PatientIntentStatsResponse(
            patient_intent_stats=[],
            total_calls_with_intent=0
        )


@router.get("/call-outcome-stats", response_model=CallOutcomeStatsResponse)
async def get_call_outcome_stats(
    region: str = "All Region",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    Get call outcome statistics
    
    Returns:
        Call outcome statistics
    """
    try:
        logger.info(f"📊 Call outcome stats for region: {region}")
        
        assistant_id = await get_assistant_id_by_region(region)
        
        base_where = "WHERE esito_chiamata IS NOT NULL AND esito_chiamata != '' AND esito_chiamata != 'NULL'"
        params = []
        param_count = 1
        
        if assistant_id:
            base_where += f" AND assistant_id = ${param_count}"
            params.append(assistant_id)
            param_count += 1
        
        if start_date and end_date:
            actual_start = max(start_date, "2024-09-26") if start_date < "2024-09-26" else start_date
            base_where += f" AND DATE(started_at) >= ${param_count} AND DATE(started_at) <= ${param_count + 1}"
            params.extend([actual_start, end_date])
        
        # Outcome stats
        outcome_query = f"""
        SELECT esito_chiamata, COUNT(*) as count
        FROM tb_stat
        {base_where}
        GROUP BY esito_chiamata
        ORDER BY count DESC
        """
        outcome_result = await db.fetch(outcome_query, *params)
        
        # Motivation by outcome
        motivation_query = f"""
        SELECT esito_chiamata, motivazione, COUNT(*) as count
        FROM tb_stat
        {base_where}
        AND motivazione IS NOT NULL AND motivazione != '' AND motivazione != 'NULL'
        GROUP BY esito_chiamata, motivazione
        ORDER BY esito_chiamata, count DESC
        """
        motivation_result = await db.fetch(motivation_query, *params)
        
        # Total
        total_query = f"SELECT COUNT(*) as total FROM tb_stat {base_where}"
        total_result = await db.fetchrow(total_query, *params)
        total_calls = total_result['total'] if total_result else 0
        
        return CallOutcomeStatsResponse(
            outcome_stats=[dict(row) for row in outcome_result],
            motivation_stats=[dict(row) for row in motivation_result],
            total_calls_with_outcome=total_calls
        )
        
    except Exception as e:
        logger.error(f"❌ Error in call outcome stats: {e}")
        return CallOutcomeStatsResponse(
            outcome_stats=[],
            motivation_stats=[],
            total_calls_with_outcome=0
        )


@router.get("/clinical-kpis", response_model=ClinicalKPIsResponse)
async def get_clinical_kpis(
    region: str = "All Region",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    Get clinical KPIs
    
    Returns:
        Clinical KPIs
    """
    try:
        logger.info(f"🏥 Clinical KPIs for region: {region}")
        
        assistant_id = await get_assistant_id_by_region(region)
        
        base_where = "WHERE started_at IS NOT NULL"
        params = []
        param_count = 1
        
        if assistant_id:
            base_where += f" AND assistant_id = ${param_count}"
            params.append(assistant_id)
            param_count += 1
        
        if start_date and end_date:
            actual_start = max(start_date, "2024-09-26") if start_date < "2024-09-26" else start_date
            base_where += f" AND DATE(started_at) >= ${param_count} AND DATE(started_at) <= ${param_count + 1}"
            params.extend([actual_start, end_date])
        
        kpi_query = f"""
        SELECT
            COUNT(*) as total_calls,
            COUNT(CASE WHEN esito_chiamata = 'COMPLETATA' AND motivazione = 'Info fornite' THEN 1 END) as completed_calls,
            COUNT(CASE WHEN esito_chiamata = 'TRASFERITA' AND motivazione IN ('Mancata comprensione', 'Argomento sconosciuto', 'Dati mancanti', 'Richiesta paziente') THEN 1 END) as transferred_calls,
            COUNT(CASE WHEN esito_chiamata = 'NON COMPLETATA' AND motivazione = 'Interrotta dal paziente' THEN 1 END) as not_completed_calls,
            COUNT(CASE WHEN patient_intent IS NOT NULL AND patient_intent != '' AND patient_intent != 'NULL' THEN 1 END) as calls_with_intent,
            COUNT(CASE WHEN esito_chiamata = 'TRASFERITA' AND motivazione = 'Richiesta paziente' THEN 1 END) as patient_requested_transfers,
            COUNT(CASE WHEN esito_chiamata = 'TRASFERITA' AND motivazione = 'Mancata comprensione' THEN 1 END) as understanding_issues,
            COUNT(CASE WHEN esito_chiamata = 'TRASFERITA' AND (motivazione = 'Argomento sconosciuto' OR motivazione = 'Dati mancanti') THEN 1 END) as unknown_topics,
            AVG(CASE WHEN duration_seconds > 0 THEN duration_seconds END) as avg_duration_seconds
        FROM tb_stat
        {base_where}
        """
        
        kpi_result = await db.fetchrow(kpi_query, *params)
        
        if kpi_result:
            total = kpi_result['total_calls']
            completion_rate = (kpi_result['completed_calls'] / total * 100) if total > 0 else 0
            transfer_rate = (kpi_result['transferred_calls'] / total * 100) if total > 0 else 0
            intent_capture_rate = (kpi_result['calls_with_intent'] / total * 100) if total > 0 else 0
            
            return ClinicalKPIsResponse(
                total_calls=total,
                completed_calls=kpi_result['completed_calls'],
                transferred_calls=kpi_result['transferred_calls'],
                not_completed_calls=kpi_result['not_completed_calls'],
                completion_rate=round(completion_rate, 2),
                transfer_rate=round(transfer_rate, 2),
                intent_capture_rate=round(intent_capture_rate, 2),
                patient_requested_transfers=kpi_result['patient_requested_transfers'],
                understanding_issues=kpi_result['understanding_issues'],
                unknown_topics=kpi_result['unknown_topics'],
                avg_duration_seconds=round(kpi_result['avg_duration_seconds'] or 0, 1)
            )
        else:
            return ClinicalKPIsResponse(
                total_calls=0, completed_calls=0, transferred_calls=0,
                not_completed_calls=0, completion_rate=0, transfer_rate=0,
                intent_capture_rate=0, patient_requested_transfers=0,
                understanding_issues=0, unknown_topics=0, avg_duration_seconds=0
            )
        
    except Exception as e:
        logger.error(f"❌ Error in clinical KPIs: {e}")
        return ClinicalKPIsResponse(
            total_calls=0, completed_calls=0, transferred_calls=0,
            not_completed_calls=0, completion_rate=0, transfer_rate=0,
            intent_capture_rate=0, patient_requested_transfers=0,
            understanding_issues=0, unknown_topics=0, avg_duration_seconds=0
        )


@router.get("/call-outcome-trend", response_model=TrendResponse)
async def get_call_outcome_trend(
    region: str = "All Region",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get call outcome trend over time"""
    try:
        assistant_id = await get_assistant_id_by_region(region)
        
        base_where = "WHERE esito_chiamata IS NOT NULL AND esito_chiamata != '' AND esito_chiamata != 'NULL'"
        params = []
        param_count = 1
        
        if assistant_id:
            base_where += f" AND assistant_id = ${param_count}"
            params.append(assistant_id)
            param_count += 1
        
        if start_date and end_date:
            actual_start = max(start_date, "2024-09-26") if start_date < "2024-09-26" else start_date
            base_where += f" AND DATE(started_at) >= ${param_count} AND DATE(started_at) <= ${param_count + 1}"
            params.extend([actual_start, end_date])
        else:
            base_where += " AND DATE(started_at) >= GREATEST('2024-09-26', CURRENT_DATE - INTERVAL '30 days')"
        
        query = f"""
        SELECT
            DATE(started_at) as date,
            esito_chiamata,
            COUNT(*) as count
        FROM tb_stat
        {base_where}
        GROUP BY DATE(started_at), esito_chiamata
        ORDER BY date DESC, esito_chiamata
        """
        
        result = await db.fetch(query, *params)
        
        return TrendResponse(
            data=[dict(row) for row in result],
            total_entries=len(result)
        )
        
    except Exception as e:
        logger.error(f"❌ Error in call outcome trend: {e}")
        return TrendResponse(data=[], total_entries=0)


@router.get("/sentiment-trend", response_model=TrendResponse)
async def get_sentiment_trend(
    region: str = "All Region",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get sentiment trend over time"""
    try:
        assistant_id = await get_assistant_id_by_region(region)
        
        base_where = "WHERE sentiment IS NOT NULL AND sentiment != '' AND sentiment != 'NULL'"
        params = []
        param_count = 1
        
        if assistant_id:
            base_where += f" AND assistant_id = ${param_count}"
            params.append(assistant_id)
            param_count += 1
        
        if start_date and end_date:
            base_where += f" AND DATE(started_at) >= ${param_count} AND DATE(started_at) <= ${param_count + 1}"
            params.extend([start_date, end_date])
        else:
            base_where += " AND DATE(started_at) >= CURRENT_DATE - INTERVAL '30 days'"
        
        query = f"""
        SELECT
            DATE(started_at) as date,
            sentiment,
            COUNT(*) as count
        FROM tb_stat
        {base_where}
        GROUP BY DATE(started_at), sentiment
        ORDER BY date DESC, sentiment
        """
        
        result = await db.fetch(query, *params)
        
        return TrendResponse(
            data=[dict(row) for row in result],
            total_entries=len(result)
        )
        
    except Exception as e:
        logger.error(f"❌ Error in sentiment trend: {e}")
        return TrendResponse(data=[], total_entries=0)
