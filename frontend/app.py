"""
Streamlit Frontend for Drone Operations AI Agent
Provides a conversational interface for the operations coordinator
"""
import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime, timedelta
import os

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Drone Operations Coordinator",
    page_icon="🚁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 0rem 0rem;
    }
    .stTabs [data-baseweb="tab-list"] button {
        font-size: 16px;
        font-weight: bold;
    }
    .conflict-critical {
        background-color: #ffcccc;
        padding: 10px;
        border-radius: 5px;
        border-left: 4px solid #ff0000;
    }
    .conflict-warning {
        background-color: #ffffcc;
        padding: 10px;
        border-radius: 5px;
        border-left: 4px solid #ffaa00;
    }
    .success-box {
        background-color: #ccffcc;
        padding: 10px;
        border-radius: 5px;
        border-left: 4px solid #00aa00;
    }
    </style>
    """, unsafe_allow_html=True)

# ============================================================================
# CONFIGURATION
# ============================================================================

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Initialize session state
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []
if "api_health" not in st.session_state:
    st.session_state.api_health = None

# ============================================================================
# HELPER FUNCTIONS (Defined Early for Streamlit)
# ============================================================================

def process_agent_query(query: str) -> str:
    """
    Process natural language query from user
    Returns a response based on query intent
    """
    query_lower = query.lower()

    # Assignment creation
    if "create assignment" in query_lower or "assign" in query_lower:
        try:
            # Extract pilot name from query
            pilots = requests.get(f"{API_BASE_URL}/api/pilots").json()
            pilot_name = None
            for pilot in pilots:
                if pilot['name'].lower() in query_lower:
                    pilot_name = pilot['name']
                    break
            
            if not pilot_name:
                return "Please specify a pilot name. Available pilots: " + ", ".join([p['name'] for p in pilots])
            
            # Get missions
            missions = requests.get(f"{API_BASE_URL}/api/missions").json()
            drones = requests.get(f"{API_BASE_URL}/api/drones").json()
            
            if not missions:
                return "No missions available to assign."
            
            # Find first available mission
            selected_mission = None
            for mission in missions:
                if mission['status'] in ['Scheduled', 'In Progress']:
                    selected_mission = mission
                    break
            
            if not selected_mission:
                return "No suitable missions found for assignment."
            
            # Find compatible drone
            compatible_drones = [d for d in drones if d['status'] == 'Available']
            if not compatible_drones:
                return "No available drones for assignment."
            
            selected_drone = compatible_drones[0]
            
            # Create assignment
            payload = {
                "pilot_name": pilot_name,
                "drone_id": selected_drone['drone_id'],
                "project_id": selected_mission['project_id'],
                "start_date": selected_mission['start_date'],
                "end_date": selected_mission['end_date']
            }
            
            result = requests.post(f"{API_BASE_URL}/api/assignments/create", json=payload).json()
            
            if result['success']:
                return f"✓ Assignment created!\n\n**Pilot:** {pilot_name}\n**Drone:** {selected_drone['drone_id']}\n**Project:** {selected_mission['project_id']}\n**Dates:** {selected_mission['start_date']} to {selected_mission['end_date']}"
            else:
                return f"✗ Assignment failed: {result['message']}"
        except Exception as e:
            return f"Error creating assignment: {str(e)}"

    # Availability queries
    elif "available" in query_lower and "pilot" in query_lower:
        try:
            payload = {}
            if "mapping" in query_lower:
                payload["skill"] = "Mapping"
            if "inspection" in query_lower:
                payload["skill"] = "Inspection"
            if "survey" in query_lower:
                payload["skill"] = "Survey"
            if "thermal" in query_lower:
                payload["skill"] = "Thermal"
            if "bangalore" in query_lower:
                payload["location"] = "Bangalore"
            if "mumbai" in query_lower:
                payload["location"] = "Mumbai"

            result = requests.post(f"{API_BASE_URL}/api/pilots/availability", json=payload).json()
            if result['matching_pilots']:
                pilots_str = "\n".join([f"  • {p['name']} ({', '.join(p['skills'])}) in {p['current_location']}" for p in result['matching_pilots']])
                return f"✓ Found {result['count']} available pilots:\n\n{pilots_str}"
            else:
                return "No pilots match the criteria."
        except Exception as e:
            return f"Error querying pilots: {str(e)}"

    # Drone queries
    elif "drone" in query_lower and ("thermal" in query_lower or "capability" in query_lower or "lidar" in query_lower or "rgb" in query_lower):
        try:
            payload = {}
            if "thermal" in query_lower:
                payload["capability"] = "Thermal"
            elif "lidar" in query_lower:
                payload["capability"] = "LiDAR"
            elif "rgb" in query_lower:
                payload["capability"] = "RGB"

            result = requests.post(f"{API_BASE_URL}/api/drones/query", json=payload).json()
            if result['matching_drones']:
                drones_str = "\n".join([f"  • {d['drone_id']} ({', '.join(d['capabilities'])}) in {d['location']}" for d in result['matching_drones']])
                return f"✓ Found {result['count']} drones with matching capabilities:\n\n{drones_str}"
            else:
                return "No drones match the criteria."
        except Exception as e:
            return f"Error querying drones: {str(e)}"

    # Conflict detection
    elif "conflict" in query_lower or "detect" in query_lower:
        try:
            result = requests.get(f"{API_BASE_URL}/api/conflicts/detect").json()
            if result['total_conflicts'] > 0:
                return f"⚠️ Found {result['total_conflicts']} conflicts in the system. Check the Conflict Detection page for details."
            else:
                return "✓ No conflicts detected!"
        except Exception as e:
            return f"Error checking for conflicts: {str(e)}"

    # Stats queries
    elif "how many" in query_lower or "total" in query_lower or "stats" in query_lower or "status" in query_lower:
        try:
            stats = requests.get(f"{API_BASE_URL}/api/stats").json()
            return f"""✓ **Fleet Statistics:**

**Pilots:**
  • Total: {stats['pilots']['total']}
  • Available: {stats['pilots']['available']}
  • On Leave: {stats['pilots']['on_leave']}
  • Unavailable: {stats['pilots']['unavailable']}

**Drones:**
  • Total: {stats['drones']['total']}
  • Available: {stats['drones']['available']}
  • Deployed: {stats['drones']['deployed']}
  • Maintenance: {stats['drones']['in_maintenance']}

**Missions:**
  • Total: {stats['missions']['total']}
  • In Progress: {stats['missions']['in_progress']}
  • Scheduled: {stats['missions']['scheduled']}"""
        except Exception as e:
            return f"Error retrieving statistics: {str(e)}"

    else:
        return """I can help with:

📋 **Examples:**
  • "Create assignment for Neha"
  • "Show available pilots in Bangalore"
  • "Show drones with thermal capability"
  • "Detect conflicts"
  • "How many pilots are available?"

What would you like to do?"""

# ============================================================================
# HEADER
# ============================================================================

st.title("🚁 Drone Operations Coordinator")
st.markdown("**AI-Powered Pilot & Drone Assignment Management**")

# Health check
try:
    response = requests.get(f"{API_BASE_URL}/api/health", timeout=2)
    if response.status_code == 200:
        st.session_state.api_health = response.json()
        st.success("✓ Backend Connected")
    else:
        st.error("✗ Backend Error")
except:
    st.error("✗ Cannot connect to backend. Make sure FastAPI server is running on http://localhost:8000")
    st.stop()

# ============================================================================
# SIDEBAR - NAVIGATION
# ============================================================================

with st.sidebar:
    st.header("Navigation")
    page = st.radio("Select Section:", [
        "Dashboard",
        "Air Agent",
        "Pilot Management",
        "Drone Fleet",
        "Assign Missions",
        "Conflict Detection",
        "Urgent Reassignments"
    ])

    st.divider()
    st.header("Quick Stats")
    if st.session_state.api_health:
        stats = st.session_state.api_health
        st.metric("Total Pilots", stats["pilots_count"])
        st.metric("Total Drones", stats["drones_count"])
        st.metric("Active Missions", stats["missions_count"])

# ============================================================================
# PAGE: DASHBOARD
# ============================================================================

if page == "Dashboard":
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("👥 Pilot Fleet Health")
        try:
            stats = requests.get(f"{API_BASE_URL}/api/stats").json()
            pilots = stats["pilots"]
            st.metric("Available", pilots["available"], f"Out of {pilots['total']}")
            st.metric("On Leave", pilots["on_leave"])
            st.metric("Unavailable", pilots["unavailable"])
        except:
            st.error("Could not load pilot stats")

    with col2:
        st.subheader("🚁 Drone Fleet Health")
        try:
            drones = stats["drones"]
            st.metric("Available", drones["available"], f"Out of {drones['total']}")
            st.metric("Deployed", drones["deployed"])
            st.metric("Maintenance", drones["in_maintenance"])
        except:
            st.error("Could not load drone stats")

    with col3:
        st.subheader("📋 Mission Status")
        try:
            missions = stats["missions"]
            st.metric("Total", missions["total"])
            st.metric("In Progress", missions["in_progress"])
            st.metric("Scheduled", missions["scheduled"])
        except:
            st.error("Could not load mission stats")

    st.divider()

    # Active Assignments
    st.subheader("📌 Active Assignments")
    try:
        assignments = requests.get(f"{API_BASE_URL}/api/assignments").json()
        if assignments:
            df = pd.DataFrame(assignments)
            df = df[['pilot_name', 'drone_id', 'project_id', 'start_date', 'end_date']]
            df.columns = ['Pilot', 'Drone', 'Project', 'Start', 'End']
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No active assignments")
    except:
        st.error("Could not load assignments")

    # Maintenance Alerts
    st.subheader("⚠️ Maintenance Alerts")
    try:
        alerts = requests.get(f"{API_BASE_URL}/api/drones/maintenance/alert").json()
        if alerts['maintenance_alerts']:
            for alert in alerts['maintenance_alerts']:
                severity = "🔴" if alert['severity'] == 'high' else "🟡"
                st.warning(f"{severity} {alert['drone_id']}: {alert['issue']}")
        else:
            st.success("No maintenance issues")
    except:
        st.error("Could not load maintenance alerts")

# ============================================================================
# PAGE: AI AGENT
# ============================================================================

elif page == "Air Agent":
    st.subheader("🤖 Conversational Operations AI")
    st.markdown("""
    Ask me anything about pilot availability, drone status, assignments, or conflicts.
    Examples:
    - "Who's available for photography in San Francisco?"
    - "Show me all drones with thermal imaging capability"
    - "Create assignment for Alice to Project Beta"
    - "Detect conflicts in current assignments"
    """)

    # AI Agent Chat Interface
    st.info("""
    **Note:** This is a demonstration of the conversational interface.
    The AI agent uses the FastAPI backend to process requests and provide intelligent responses.
    """)

    # Chat history
    for message in st.session_state.conversation_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # User input
    user_input = st.chat_input("Ask me about drone operations...")

    if user_input:
        # Add user message to history
        st.session_state.conversation_history.append({
            "role": "user",
            "content": user_input
        })

        # Process request (simplified AI logic)
        response = process_agent_query(user_input)

        # Add assistant response to history
        st.session_state.conversation_history.append({
            "role": "assistant",
            "content": response
        })

        # Rerun to display messages
        st.rerun()

# ============================================================================
# PAGE: PILOT MANAGEMENT
# ============================================================================

elif page == "Pilot Management":
    st.subheader("👥 Pilot Roster Management")

    tab1, tab2, tab3 = st.tabs(["View Pilots", "Query Availability", "Update Status"])

    with tab1:
        st.markdown("### All Pilots")
        try:
            pilots = requests.get(f"{API_BASE_URL}/api/pilots").json()
            df = pd.DataFrame(pilots)
            df = df[['name', 'skills', 'certifications', 'current_location', 'status', 'availability']]
            st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"Error loading pilots: {str(e)}")

    with tab2:
        st.markdown("### Query Pilot Availability")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            skill_filter = st.text_input("Filter by skill (e.g., Photography):", key="skill_input")
        with col2:
            cert_filter = st.text_input("Filter by certification:", key="cert_input")
        with col3:
            location_filter = st.text_input("Filter by location:", key="location_input")
        with col4:
            query_btn = st.button("Query", key="query_pilots")

        if query_btn or skill_filter or cert_filter or location_filter:
            try:
                payload = {}
                if skill_filter:
                    payload["skill"] = skill_filter
                if cert_filter:
                    payload["certification"] = cert_filter
                if location_filter:
                    payload["location"] = location_filter

                result = requests.post(
                    f"{API_BASE_URL}/api/pilots/availability",
                    json=payload
                ).json()

                st.markdown(f"### Found {result['count']} matching pilots")
                if result['matching_pilots']:
                    df = pd.DataFrame(result['matching_pilots'])
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No pilots match the criteria")
            except Exception as e:
                st.error(f"Query error: {str(e)}")

    with tab3:
        st.markdown("### Update Pilot Status")
        col1, col2, col3 = st.columns(3)

        with col1:
            try:
                pilots = requests.get(f"{API_BASE_URL}/api/pilots").json()
                pilot_names = [p['name'] for p in pilots]
                selected_pilot = st.selectbox("Select Pilot:", pilot_names, key="pilot_select")
            except:
                st.error("Could not load pilots")
                selected_pilot = None

        with col2:
            new_status = st.selectbox(
                "New Status:",
                ["Available", "On Leave", "Unavailable"],
                key="status_select"
            )

        with col3:
            update_btn = st.button("Update", key="update_pilot_btn")

        if update_btn and selected_pilot:
            try:
                payload = {
                    "name": selected_pilot,
                    "status": new_status
                }
                result = requests.put(
                    f"{API_BASE_URL}/api/pilots/{selected_pilot}/status",
                    json=payload
                ).json()

                if result['success']:
                    st.markdown("<div class='success-box'>✓ Status updated successfully</div>", unsafe_allow_html=True)
                    st.info(f"**Sync Status:**\n" + "\n".join(result['sync_log']))
                else:
                    st.error(result['message'])
            except Exception as e:
                st.error(f"Update error: {str(e)}")

# ============================================================================
# PAGE: DRONE FLEET
# ============================================================================

elif page == "Drone Fleet":
    st.subheader("🚁 Drone Fleet Management")

    tab1, tab2, tab3 = st.tabs(["Fleet Status", "Query Fleet", "Update Drone"])

    with tab1:
        st.markdown("### Complete Fleet Status")
        try:
            drones = requests.get(f"{API_BASE_URL}/api/drones").json()
            df = pd.DataFrame(drones)
            df = df[['drone_id', 'model', 'capabilities', 'status', 'location', 'maintenance_due']]
            st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"Error loading drones: {str(e)}")

    with tab2:
        st.markdown("### Query Fleet")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            capability_filter = st.text_input("Filter by capability:", key="cap_input")
        with col2:
            location_filter = st.text_input("Filter by location:", key="drone_loc_input")
        with col3:
            status_filter = st.selectbox(
                "Filter by status:",
                ["", "Available", "Deployed", "In Maintenance"],
                key="drone_status_input"
            )
        with col4:
            query_btn = st.button("Query", key="query_drones")

        if query_btn or capability_filter or location_filter or status_filter:
            try:
                payload = {}
                if capability_filter:
                    payload["capability"] = capability_filter
                if location_filter:
                    payload["location"] = location_filter
                if status_filter:
                    payload["status"] = status_filter

                result = requests.post(
                    f"{API_BASE_URL}/api/drones/query",
                    json=payload
                ).json()

                st.markdown(f"### Found {result['count']} matching drones")
                if result['matching_drones']:
                    df = pd.DataFrame(result['matching_drones'])
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No drones match the criteria")
            except Exception as e:
                st.error(f"Query error: {str(e)}")

    with tab3:
        st.markdown("### Update Drone Status")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            try:
                drones = requests.get(f"{API_BASE_URL}/api/drones").json()
                drone_ids = [d['drone_id'] for d in drones]
                selected_drone = st.selectbox("Select Drone:", drone_ids, key="drone_select")
            except:
                st.error("Could not load drones")
                selected_drone = None

        with col2:
            new_status = st.selectbox(
                "New Status:",
                ["Available", "Deployed", "In Maintenance"],
                key="drone_status_select"
            )

        with col3:
            new_location = st.text_input("New Location (optional):", key="drone_loc_select")

        with col4:
            update_btn = st.button("Update", key="update_drone_btn")

        if update_btn and selected_drone:
            try:
                payload = {
                    "drone_id": selected_drone,
                    "status": new_status
                }
                if new_location:
                    payload["location"] = new_location

                result = requests.put(
                    f"{API_BASE_URL}/api/drones/{selected_drone}/status",
                    json=payload
                ).json()

                if result['success']:
                    st.markdown("<div class='success-box'>✓ Drone updated successfully</div>", unsafe_allow_html=True)
                    st.info(f"**Sync Status:**\n" + "\n".join(result['sync_log']))
                else:
                    st.error(result['message'])
            except Exception as e:
                st.error(f"Update error: {str(e)}")

# ============================================================================
# PAGE: ASSIGN MISSIONS
# ============================================================================

elif page == "Assign Missions":
    st.subheader("📋 Assign Pilots & Drones to Missions")

    st.info("""
    The system will validate the assignment for:
    - Skill/certification match
    - No double-booking conflicts
    - Location compatibility
    - Drone maintenance status
    """)

    col1, col2, col3 = st.columns(3)

    with col1:
        try:
            pilots = requests.get(f"{API_BASE_URL}/api/pilots").json()
            pilot_names = [p['name'] for p in pilots]
            selected_pilot = st.selectbox("Select Pilot:", pilot_names)
        except:
            st.error("Could not load pilots")
            selected_pilot = None

    with col2:
        try:
            drones = requests.get(f"{API_BASE_URL}/api/drones").json()
            drone_ids = [d['drone_id'] for d in drones if d['status'] == 'Available']
            selected_drone = st.selectbox("Select Drone:", drone_ids)
        except:
            st.error("Could not load drones")
            selected_drone = None

    with col3:
        try:
            missions = requests.get(f"{API_BASE_URL}/api/missions").json()
            project_ids = [m['project_id'] for m in missions]
            selected_project = st.selectbox("Select Project:", project_ids)
        except:
            st.error("Could not load missions")
            selected_project = None

    col4, col5 = st.columns(2)
    with col4:
        start_date = st.date_input("Start Date")
    with col5:
        end_date = st.date_input("End Date")

    if st.button("Validate Assignment"):
        if selected_pilot and selected_drone and selected_project:
            try:
                payload = {
                    "pilot_name": selected_pilot,
                    "drone_id": selected_drone,
                    "project_id": selected_project,
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d")
                }

                result = requests.post(
                    f"{API_BASE_URL}/api/assignments/validate",
                    json=payload
                ).json()

                st.markdown("### Validation Report")
                st.metric("Conflicts Found", result['conflicts_found'])
                st.metric("Critical", result['critical_count'])
                st.metric("Warnings", result['warning_count'])

                if result['conflicts']:
                    st.markdown("### Issues Detected")
                    for conflict in result['conflicts']:
                        severity_icon = "🔴" if conflict['severity'] == 'critical' else "🟡"
                        with st.expander(f"{severity_icon} {conflict['type'].upper()}"):
                            st.markdown(f"**Description:** {conflict['description']}")
                            if conflict['suggestion']:
                                st.markdown(f"**Suggestion:** {conflict['suggestion']}")
                else:
                    st.success("✓ No conflicts detected!")

            except Exception as e:
                st.error(f"Validation error: {str(e)}")

    if st.button("Create Assignment"):
        if selected_pilot and selected_drone and selected_project:
            try:
                payload = {
                    "pilot_name": selected_pilot,
                    "drone_id": selected_drone,
                    "project_id": selected_project,
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d")
                }

                result = requests.post(
                    f"{API_BASE_URL}/api/assignments/create",
                    json=payload
                ).json()

                if result['success']:
                    st.markdown("<div class='success-box'>✓ Assignment created successfully!</div>", unsafe_allow_html=True)
                    st.json(result['assignment'])
                    if result['warnings']:
                        st.warning(f"**Warnings:** {chr(10).join(result['warnings'])}")
                else:
                    st.error(result['message'])
                    if result['warnings']:
                        for warning in result['warnings']:
                            st.warning(warning)
            except Exception as e:
                st.error(f"Creation error: {str(e)}")

# ============================================================================
# PAGE: CONFLICT DETECTION
# ============================================================================

elif page == "Conflict Detection":
    st.subheader("⚠️ System Conflict Detection")

    if st.button("Scan for All Conflicts"):
        try:
            result = requests.get(f"{API_BASE_URL}/api/conflicts/detect").json()
            st.metric("Total Conflicts", result['total_conflicts'])

            if result['conflicts']:
                st.markdown("### Detected Conflicts")
                for conflict in result['conflicts']:
                    severity_class = "conflict-critical" if conflict['severity'] == 'critical' else "conflict-warning"
                    severity_icon = "🔴" if conflict['severity'] == 'critical' else "🟡"

                    with st.expander(f"{severity_icon} {conflict['type']} - {conflict['affected_entity']}"):
                        st.markdown(f"**Description:** {conflict['description']}")
                        if conflict['suggestion']:
                            st.markdown(f"**Suggestion:** {conflict['suggestion']}")
            else:
                st.success("✓ No conflicts detected!")
        except Exception as e:
            st.error(f"Error: {str(e)}")

# ============================================================================
# PAGE: URGENT REASSIGNMENTS
# ============================================================================

elif page == "Urgent Reassignments":
    st.subheader("🚨 Urgent Pilot Assignments & Reassignments")

    st.info("""
    Use this feature to handle urgent assignments/reassignments:
    - Assign available pilots to high-priority projects
    - Reassign pilots due to project changes or conflicts
    - Automatically resolve assignment conflicts
    - Find compatible drones automatically
    """)

    col1, col2 = st.columns(2)

    with col1:
        try:
            pilots = requests.get(f"{API_BASE_URL}/api/pilots").json()
            all_pilots = [p['name'] for p in pilots]
            selected_pilot = st.selectbox("Select Pilot:", all_pilots)
        except:
            st.error("Could not load pilots")
            selected_pilot = None

    with col2:
        try:
            missions = requests.get(f"{API_BASE_URL}/api/missions").json()
            project_ids = [m['project_id'] for m in missions]
            selected_project = st.selectbox("Assign to Project:", project_ids)
        except:
            st.error("Could not load missions")
            selected_project = None

    reason = st.selectbox(
        "Reason for Reassignment:",
        ["emergency", "conflict_resolution", "performance", "availability"]
    )

    if st.button("Execute Urgent Reassignment"):
        if selected_pilot and selected_project:
            try:
                payload = {
                    "pilot_name": selected_pilot,
                    "new_project_id": selected_project,
                    "reason": reason
                }

                response = requests.post(
                    f"{API_BASE_URL}/api/reassignments/urgent",
                    json=payload,
                    timeout=10
                )
                
                if response.status_code != 200:
                    st.error(f"API Error {response.status_code}: {response.text}")
                    st.stop()
                
                result = response.json()

                if result['success']:
                    st.markdown("<div class='success-box'>✓ Reassignment successful!</div>", unsafe_allow_html=True)
                    st.markdown(f"**Pilot:** {selected_pilot}")
                    st.markdown(f"**Drone:** (Auto-selected)")
                    st.markdown(f"**From:** {result.get('old_assignment', 'Unassigned')}")
                    st.markdown(f"**To:** {result['new_assignment']}")
                    st.markdown(f"**Reason:** {reason}")
                    if result.get('conflicts_resolved'):
                        with st.expander("Conflicts Detected & Resolved"):
                            for conflict in result['conflicts_resolved']:
                                st.info(f"• {conflict.get('description', 'Unknown conflict')}")
                else:
                    st.error(f"❌ {result.get('message', 'Assignment failed')}")
                    if result.get('conflicts_resolved'):
                        with st.expander("View Conflicts"):
                            for conflict in result['conflicts_resolved']:
                                st.warning(f"• {conflict.get('description', 'Unknown conflict')}")
            except requests.exceptions.RequestException as e:
                st.error(f"Connection error: {str(e)}")
            except ValueError as e:
                st.error(f"Invalid response from server: {str(e)}")
            except Exception as e:
                st.error(f"Reassignment error: {str(e)}")

# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.markdown("""
    <div style='text-align: center; color: gray; font-size: 12px;'>
    Skylark Drones Operations Coordinator • Powered by FastAPI + Streamlit + OpenAI
    </div>
    """, unsafe_allow_html=True)
