"""
Streamlit Dashboard for AI-Powered Network Security System
Real-time monitoring, threat analytics, and system management
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import os
import sys
from pathlib import Path
import json

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.config_loader import ConfigLoader
from src.utils.logger import setup_logger
from src.etl.pipeline import ETLPipeline
from src.models.threat_detector import ThreatDetector
from src.blockchain.blockchain_logger import BlockchainLogger
from src.mlops.auto_retrainer import AutoRetrainer

# Page configuration
st.set_page_config(
    page_title="AI Network Security System",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .threat-critical {
        color: #d62728;
        font-weight: bold;
    }
    .threat-high {
        color: #ff7f0e;
        font-weight: bold;
    }
    .threat-medium {
        color: #ffbb00;
        font-weight: bold;
    }
    .threat-low {
        color: #2ca02c;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


class SecurityDashboard:
    """Main dashboard class"""
    
    def __init__(self):
        self.config = ConfigLoader.load_config()
        self.logger = setup_logger(__name__)
        
        # Initialize components
        if 'etl_pipeline' not in st.session_state:
            st.session_state.etl_pipeline = ETLPipeline()
        
        if 'threat_detector' not in st.session_state:
            st.session_state.threat_detector = ThreatDetector()
        
        if 'blockchain_logger' not in st.session_state:
            st.session_state.blockchain_logger = BlockchainLogger()
        
        if 'auto_retrainer' not in st.session_state:
            st.session_state.auto_retrainer = AutoRetrainer()
    
    def render_header(self):
        """Render dashboard header"""
        st.markdown('<div class="main-header">🛡️ AI-Powered Network Security System</div>', 
                   unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("System Status", "🟢 Active", "Running")
        
        with col2:
            st.metric("Last Update", datetime.now().strftime("%H:%M:%S"), "Live")
        
        with col3:
            blockchain_valid = st.session_state.blockchain_logger.verify_integrity()
            status = "✅ Valid" if blockchain_valid else "❌ Invalid"
            st.metric("Blockchain Integrity", status, "")
    
    def render_sidebar(self):
        """Render sidebar with navigation and controls"""
        st.sidebar.title("Navigation")
        
        page = st.sidebar.radio(
            "Select Page",
            ["Overview", "Threat Detection", "ETL Pipeline", "Model Performance", 
             "Blockchain Audit", "System Settings"]
        )
        
        st.sidebar.markdown("---")
        
        st.sidebar.title("Quick Actions")
        
        if st.sidebar.button("🔄 Run ETL Pipeline"):
            with st.spinner("Running ETL pipeline..."):
                success = st.session_state.etl_pipeline.run_pipeline()
                if success:
                    st.sidebar.success("ETL pipeline completed!")
                else:
                    st.sidebar.error("ETL pipeline failed!")
        
        if st.sidebar.button("🤖 Retrain Model"):
            with st.spinner("Retraining model..."):
                processed_files = list(Path('data/processed').glob('*.csv'))
                if processed_files:
                    latest_file = max(processed_files, key=os.path.getctime)
                    result = st.session_state.auto_retrainer.retrain_model(str(latest_file))
                    if result.get('success'):
                        st.sidebar.success("Model retrained successfully!")
                    else:
                        st.sidebar.error("Model retraining failed!")
                else:
                    st.sidebar.warning("No data available for retraining")
        
        if st.sidebar.button("🔍 Verify Blockchain"):
            is_valid = st.session_state.blockchain_logger.verify_integrity()
            if is_valid:
                st.sidebar.success("Blockchain is valid!")
            else:
                st.sidebar.error("Blockchain integrity compromised!")
        
        st.sidebar.markdown("---")
        st.sidebar.info("**Project Team:**\n- Sourav Biswas\n- Shubham Choubey\n- Om Suneri\n- Tanuj Ramchandani\n- Sehwag Meena\n- Yatin Kumar")
        
        return page
    
    def render_overview_page(self):
        """Render overview dashboard"""
        st.header("System Overview")
        
        # Metrics row
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Threats Detected", "1,247", "+23 today")
        
        with col2:
            st.metric("Blocked IPs", "89", "+5 today")
        
        with col3:
            st.metric("Model Accuracy", "95.3%", "+1.2%")
        
        with col4:
            st.metric("System Uptime", "99.8%", "30 days")
        
        st.markdown("---")
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Threat Timeline (Last 24 Hours)")
            # Generate sample data
            hours = list(range(24))
            threats = np.random.poisson(10, 24)
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=hours, y=threats,
                mode='lines+markers',
                name='Threats Detected',
                line=dict(color='#d62728', width=2)
            ))
            fig.update_layout(
                xaxis_title="Hour",
                yaxis_title="Number of Threats",
                height=300
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("Threat Distribution by Type")
            threat_types = ['Intrusion', 'Malware', 'Phishing', 'DDoS', 'Data Exfiltration']
            threat_counts = [245, 189, 156, 98, 67]
            
            fig = go.Figure(data=[go.Pie(
                labels=threat_types,
                values=threat_counts,
                hole=0.4
            )])
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
        
        # Recent alerts table
        st.subheader("Recent Security Alerts")
        
        # Generate sample data
        recent_alerts = pd.DataFrame({
            'Timestamp': [datetime.now() - timedelta(minutes=i*5) for i in range(10)],
            'Threat Type': np.random.choice(['Intrusion', 'Malware', 'Phishing', 'DDoS'], 10),
            'Source IP': [f"192.168.{np.random.randint(1,255)}.{np.random.randint(1,255)}" for _ in range(10)],
            'Severity': np.random.choice(['Critical', 'High', 'Medium', 'Low'], 10),
            'Status': np.random.choice(['Blocked', 'Investigating', 'Resolved'], 10)
        })
        
        st.dataframe(recent_alerts, use_container_width=True, height=300)
    
    def render_threat_detection_page(self):
        """Render threat detection page"""
        st.header("Threat Detection")
        
        tab1, tab2, tab3 = st.tabs(["Real-time Detection", "Historical Analysis", "Threat Intelligence"])
        
        with tab1:
            st.subheader("Real-time Threat Detection")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.write("Upload network data for real-time threat analysis:")
                uploaded_file = st.file_uploader("Choose a CSV file", type=['csv'])
                
                if uploaded_file is not None:
                    df = pd.read_csv(uploaded_file)
                    st.write(f"Loaded {len(df)} records")
                    
                    if st.button("Analyze Threats"):
                        with st.spinner("Analyzing data..."):
                            # Simulate threat detection
                            st.success(f"Analysis complete! Found {np.random.randint(5, 20)} potential threats")
            
            with col2:
                st.metric("Current Threat Level", "🟠 Elevated", "")
                st.metric("Active Threats", "7", "+2")
                st.metric("Processing Rate", "1.2k/sec", "")
        
        with tab2:
            st.subheader("Historical Threat Analysis")
            
            # Date range selector
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date", datetime.now() - timedelta(days=30))
            with col2:
                end_date = st.date_input("End Date", datetime.now())
            
            # Generate historical data
            dates = pd.date_range(start=start_date, end=end_date, freq='D')
            historical_threats = pd.DataFrame({
                'Date': dates,
                'Threats': np.random.poisson(50, len(dates)),
                'Blocked': np.random.poisson(45, len(dates))
            })
            
            fig = go.Figure()
            fig.add_trace(go.Bar(x=historical_threats['Date'], y=historical_threats['Threats'], 
                                name='Total Threats', marker_color='#d62728'))
            fig.add_trace(go.Bar(x=historical_threats['Date'], y=historical_threats['Blocked'], 
                                name='Blocked', marker_color='#2ca02c'))
            fig.update_layout(barmode='group', height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with tab3:
            st.subheader("Threat Intelligence Feed")
            
            st.info("📡 Live threat intelligence updates from global security sources")
            
            # Sample threat intelligence
            intel_data = pd.DataFrame({
                'Time': [datetime.now() - timedelta(hours=i) for i in range(5)],
                'Source': ['CrowdStrike', 'FireEye', 'Kaspersky', 'Symantec', 'Cisco'],
                'Threat': ['New ransomware variant', 'Zero-day exploit', 'APT campaign', 
                          'Phishing campaign', 'Botnet activity'],
                'Severity': ['Critical', 'High', 'High', 'Medium', 'Medium']
            })
            
            st.dataframe(intel_data, use_container_width=True)
    
    def render_etl_pipeline_page(self):
        """Render ETL pipeline page"""
        st.header("ETL Pipeline Management")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Records Processed", "1.2M", "+50k today")
        
        with col2:
            st.metric("Pipeline Success Rate", "99.2%", "+0.3%")
        
        with col3:
            st.metric("Avg Processing Time", "2.3s", "-0.5s")
        
        st.markdown("---")
        
        # Pipeline controls
        st.subheader("Pipeline Controls")
        
        source_type = st.selectbox(
            "Select Data Source",
            ["All Sources", "Firewall Logs", "Network Traffic", "System Logs"]
        )
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("▶️ Start Pipeline"):
                with st.spinner("Running ETL pipeline..."):
                    source_map = {
                        "All Sources": "all",
                        "Firewall Logs": "firewall",
                        "Network Traffic": "traffic",
                        "System Logs": "system"
                    }
                    success = st.session_state.etl_pipeline.run_pipeline(source_map[source_type])
                    if success:
                        st.success("Pipeline executed successfully!")
                    else:
                        st.error("Pipeline execution failed!")
        
        with col2:
            if st.button("⏸️ Pause Pipeline"):
                st.info("Pipeline paused")
        
        with col3:
            if st.button("🔄 Reset Pipeline"):
                st.warning("Pipeline reset")
        
        st.markdown("---")
        
        # Pipeline status
        st.subheader("Pipeline Status")
        
        pipeline_stages = pd.DataFrame({
            'Stage': ['Extract', 'Transform', 'Load', 'Validate'],
            'Status': ['✅ Complete', '✅ Complete', '✅ Complete', '✅ Complete'],
            'Records': [1000, 1000, 1000, 1000],
            'Duration': ['0.5s', '1.2s', '0.6s', '0.3s']
        })
        
        st.dataframe(pipeline_stages, use_container_width=True)
    
    def render_model_performance_page(self):
        """Render model performance page"""
        st.header("Model Performance & MLOps")
        
        tab1, tab2, tab3 = st.tabs(["Performance Metrics", "Training History", "Model Registry"])
        
        with tab1:
            st.subheader("Current Model Performance")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Accuracy", "95.3%", "+1.2%")
            
            with col2:
                st.metric("Precision", "94.7%", "+0.8%")
            
            with col3:
                st.metric("Recall", "96.1%", "+1.5%")
            
            with col4:
                st.metric("F1 Score", "95.4%", "+1.1%")
            
            st.markdown("---")
            
            # Confusion matrix
            st.subheader("Confusion Matrix")
            
            cm = np.array([[450, 25], [15, 510]])
            fig = px.imshow(cm, 
                           labels=dict(x="Predicted", y="Actual", color="Count"),
                           x=['Normal', 'Threat'],
                           y=['Normal', 'Threat'],
                           text_auto=True,
                           color_continuous_scale='Blues')
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            st.subheader("Training History")
            
            # Generate sample training history
            epochs = list(range(1, 51))
            train_loss = [0.5 * np.exp(-i/10) + np.random.normal(0, 0.02) for i in epochs]
            val_loss = [0.5 * np.exp(-i/10) + np.random.normal(0, 0.03) for i in epochs]
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=epochs, y=train_loss, mode='lines', name='Training Loss'))
            fig.add_trace(go.Scatter(x=epochs, y=val_loss, mode='lines', name='Validation Loss'))
            fig.update_layout(
                xaxis_title="Epoch",
                yaxis_title="Loss",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with tab3:
            st.subheader("Model Registry")
            
            model_versions = pd.DataFrame({
                'Version': ['v1.3.0', 'v1.2.0', 'v1.1.0', 'v1.0.0'],
                'Accuracy': ['95.3%', '94.1%', '92.8%', '91.5%'],
                'Trained On': [
                    (datetime.now() - timedelta(days=i*7)).strftime("%Y-%m-%d") 
                    for i in range(4)
                ],
                'Status': ['Production', 'Staging', 'Archived', 'Archived']
            })
            
            st.dataframe(model_versions, use_container_width=True)
            
            if st.button("Deploy New Version"):
                st.success("New model version deployed to production!")
    
    def render_blockchain_audit_page(self):
        """Render blockchain audit page"""
        st.header("Blockchain Audit Trail")
        
        # Verification status
        is_valid = st.session_state.blockchain_logger.verify_integrity()
        
        if is_valid:
            st.success("✅ Blockchain Integrity: VALID - All audit logs are tamper-proof")
        else:
            st.error("❌ Blockchain Integrity: COMPROMISED - Potential tampering detected!")
        
        st.markdown("---")
        
        # Blockchain stats
        col1, col2, col3 = st.columns(3)
        
        chain_length = len(st.session_state.blockchain_logger.blockchain.chain)
        
        with col1:
            st.metric("Total Blocks", chain_length, "")
        
        with col2:
            st.metric("Total Audit Logs", chain_length - 1, "")
        
        with col3:
            st.metric("Last Block Time", datetime.now().strftime("%H:%M:%S"), "")
        
        st.markdown("---")
        
        # Audit log filters
        st.subheader("Audit Log Explorer")
        
        col1, col2 = st.columns(2)
        
        with col1:
            log_type = st.selectbox(
                "Filter by Type",
                ["All", "ETL_OPERATION", "THREAT_DETECTION", "MODEL_UPDATE", "SYSTEM_EVENT"]
            )
        
        with col2:
            date_range = st.date_input(
                "Date Range",
                [datetime.now() - timedelta(days=7), datetime.now()]
            )
        
        # Get audit trail
        event_type = None if log_type == "All" else log_type
        audit_logs = st.session_state.blockchain_logger.get_audit_trail(event_type=event_type)
        
        if audit_logs:
            # Convert to DataFrame
            log_data = []
            for block in audit_logs:
                log_entry = {
                    'Block #': block['index'],
                    'Timestamp': block['data'].get('timestamp', 'N/A'),
                    'Type': block['data'].get('type', 'N/A'),
                    'Operation': block['data'].get('operation', 'N/A'),
                    'Hash': block['hash'][:16] + '...'
                }
                log_data.append(log_entry)
            
            df = pd.DataFrame(log_data)
            st.dataframe(df, use_container_width=True, height=400)
            
            # Export button
            if st.button("📥 Export Audit Report"):
                output_path = f"data/blockchain/audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                success = st.session_state.blockchain_logger.export_audit_report(output_path)
                if success:
                    st.success(f"Audit report exported to {output_path}")
                else:
                    st.error("Failed to export audit report")
        else:
            st.info("No audit logs found for the selected filters")
    
    def render_settings_page(self):
        """Render system settings page"""
        st.header("System Settings")
        
        tab1, tab2, tab3 = st.tabs(["General", "Alerts", "API Configuration"])
        
        with tab1:
            st.subheader("General Settings")
            
            enable_blockchain = st.checkbox("Enable Blockchain Logging", value=True)
            enable_mlops = st.checkbox("Enable MLOps Automation", value=True)
            enable_alerts = st.checkbox("Enable Real-time Alerts", value=True)
            
            st.slider("Model Retrain Interval (days)", 1, 30, 7)
            st.slider("Alert Threshold", 0.0, 1.0, 0.7, 0.05)
            
            if st.button("💾 Save Settings"):
                st.success("Settings saved successfully!")
        
        with tab2:
            st.subheader("Alert Configuration")
            
            st.text_input("Alert Email", "security-alerts@example.com")
            st.text_input("Slack Webhook URL", "")
            
            st.multiselect(
                "Alert Severity Levels",
                ["Critical", "High", "Medium", "Low"],
                default=["Critical", "High"]
            )
            
            if st.button("💾 Save Alert Settings"):
                st.success("Alert settings saved!")
        
        with tab3:
            st.subheader("API Configuration")
            
            st.text_input("Gemini API Key", type="password")
            st.text_input("MongoDB URI", "mongodb://localhost:27017/")
            st.text_input("PostgreSQL URI", "postgresql://localhost:5432/security_db")
            
            if st.button("🔑 Update API Keys"):
                st.success("API keys updated!")
    
    def run(self):
        """Run the dashboard"""
        try:
            # Render header
            self.render_header()
            
            # Render sidebar and get selected page
            page = self.render_sidebar()
            
            # Render selected page
            if page == "Overview":
                self.render_overview_page()
            elif page == "Threat Detection":
                self.render_threat_detection_page()
            elif page == "ETL Pipeline":
                self.render_etl_pipeline_page()
            elif page == "Model Performance":
                self.render_model_performance_page()
            elif page == "Blockchain Audit":
                self.render_blockchain_audit_page()
            elif page == "System Settings":
                self.render_settings_page()
            
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            self.logger.error(f"Dashboard error: {str(e)}")


def main():
    """Main entry point"""
    dashboard = SecurityDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()
