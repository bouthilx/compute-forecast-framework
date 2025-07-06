"""
Unit tests for alert suppression functionality.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from compute_forecast.monitoring.alert_suppression import AlertSuppressionManager, SuppressionRuleManager
from compute_forecast.monitoring.alert_structures import Alert, SuppressionRule


class TestAlertSuppressionManager:
    """Test AlertSuppressionManager functionality"""
    
    @pytest.fixture
    def suppression_manager(self):
        """Create test suppression manager"""
        return AlertSuppressionManager()
    
    @pytest.fixture
    def test_alert(self):
        """Create test alert"""
        return Alert(
            alert_id="test_alert_001",
            rule_id="test_rule",
            timestamp=datetime.now(),
            severity="warning",
            title="Test Alert Title",
            message="Test alert message",
            affected_components=["test_component"],
            current_value=100,
            threshold_value=50,
            metrics_context={},
            recommended_actions=["Test action"],
            status="active"
        )
    
    def test_initialization(self, suppression_manager):
        """Test suppression manager initialization"""
        assert len(suppression_manager.suppression_rules) == 0
        assert len(suppression_manager.auto_suppressed_alerts) == 0
        assert suppression_manager.suppression_stats['total_suppressions'] == 0
    
    def test_add_suppression_rule(self, suppression_manager):
        """Test adding suppression rules"""
        rule_id = suppression_manager.add_suppression_rule(
            pattern="test_alert",
            duration_minutes=30,
            reason="Testing suppression"
        )
        
        assert rule_id is not None
        assert rule_id in suppression_manager.suppression_rules
        assert suppression_manager.suppression_stats['total_suppressions'] == 1
        
        rule = suppression_manager.suppression_rules[rule_id]
        assert rule.pattern == "test_alert"
        assert rule.duration_minutes == 30
        assert rule.reason == "Testing suppression"
        assert rule.is_active()
    
    def test_remove_suppression_rule_by_pattern(self, suppression_manager):
        """Test removing suppression rules by pattern"""
        # Add rule
        suppression_manager.add_suppression_rule(
            pattern="test_pattern",
            duration_minutes=30,
            reason="Test"
        )
        
        assert len(suppression_manager.suppression_rules) == 1
        
        # Remove by pattern
        removed = suppression_manager.remove_suppression_rule("test_pattern")
        
        assert removed is True
        assert len(suppression_manager.suppression_rules) == 0
    
    def test_remove_suppression_rule_by_id(self, suppression_manager):
        """Test removing suppression rules by ID"""
        rule_id = suppression_manager.add_suppression_rule(
            pattern="test_pattern",
            duration_minutes=30,
            reason="Test"
        )
        
        assert len(suppression_manager.suppression_rules) == 1
        
        # Remove by ID
        removed = suppression_manager.remove_suppression_rule_by_id(rule_id)
        
        assert removed is True
        assert len(suppression_manager.suppression_rules) == 0
    
    def test_is_suppressed_with_manual_rule(self, suppression_manager, test_alert):
        """Test suppression with manual rules"""
        # Should not be suppressed initially
        assert not suppression_manager.is_suppressed(test_alert)
        
        # Add suppression rule that matches
        suppression_manager.add_suppression_rule(
            pattern="test alert",  # Should match title
            duration_minutes=30,
            reason="Test suppression"
        )
        
        # Should now be suppressed
        assert suppression_manager.is_suppressed(test_alert)
    
    def test_is_suppressed_with_auto_suppression(self, suppression_manager, test_alert):
        """Test auto-suppression functionality"""
        # Should not be suppressed initially
        assert not suppression_manager.is_suppressed(test_alert)
        
        # Add auto-suppression for the alert's rule
        suppression_manager.auto_suppress_alert_rule("test_rule", 30)
        
        # Should now be suppressed
        assert suppression_manager.is_suppressed(test_alert)
    
    def test_cleanup_expired_suppressions(self, suppression_manager):
        """Test cleanup of expired suppression rules"""
        # Add rule that expires immediately
        rule_id = suppression_manager.add_suppression_rule(
            pattern="test",
            duration_minutes=0,  # Expires immediately
            reason="Test expiration"
        )
        
        assert len(suppression_manager.suppression_rules) == 1
        
        # Cleanup should remove expired rule
        suppression_manager.cleanup_expired_suppressions()
        
        assert len(suppression_manager.suppression_rules) == 0
    
    def test_get_active_suppressions(self, suppression_manager):
        """Test getting active suppression rules"""
        # Add some rules
        suppression_manager.add_suppression_rule("pattern1", 30, "Test 1")
        suppression_manager.add_suppression_rule("pattern2", 60, "Test 2")
        suppression_manager.auto_suppress_alert_rule("rule1", 45)
        
        active = suppression_manager.get_active_suppressions()
        
        assert len(active) == 3
        
        # Check structure
        for suppression in active:
            assert 'rule_id' in suppression
            assert 'type' in suppression
            assert 'pattern' in suppression
            assert 'reason' in suppression
            assert 'remaining_minutes' in suppression
            assert suppression['type'] in ['manual', 'auto']
    
    def test_get_suppression_statistics(self, suppression_manager):
        """Test getting suppression statistics"""
        # Add some suppressions
        suppression_manager.add_suppression_rule("pattern1", 30, "Test 1")
        suppression_manager.auto_suppress_alert_rule("rule1", 45)
        
        stats = suppression_manager.get_suppression_statistics()
        
        assert stats['total_suppressions_created'] == 1  # Only manual rules count
        assert stats['active_suppression_rules'] == 1
        assert stats['active_auto_suppressions'] == 1
        assert stats['total_active_suppressions'] == 2
    
    def test_suppress_similar_alerts(self, suppression_manager, test_alert):
        """Test suppressing similar alerts"""
        suppression_manager.suppress_similar_alerts(test_alert, 60)
        
        # Should create a suppression rule based on rule_id and severity
        active = suppression_manager.get_active_suppressions()
        assert len(active) == 1
        
        rule = active[0]
        assert rule['pattern'] == "test_rule_warning"
        assert rule['type'] == 'manual'
    
    def test_bulk_suppress_by_component(self, suppression_manager):
        """Test bulk suppression by component"""
        suppression_manager.bulk_suppress_by_component(
            component="API_LAYER",
            duration_minutes=30,
            reason="Maintenance window"
        )
        
        active = suppression_manager.get_active_suppressions()
        assert len(active) == 1
        
        rule = active[0]
        assert "api_layer" in rule['pattern'].lower()
        assert "maintenance" in rule['reason'].lower()
    
    def test_emergency_suppress_all(self, suppression_manager):
        """Test emergency suppression of all alerts"""
        suppression_manager.emergency_suppress_all(15)
        
        active = suppression_manager.get_active_suppressions()
        assert len(active) == 1
        
        rule = active[0]
        assert rule['pattern'] == "*"
        assert "emergency" in rule['reason'].lower()


class TestSuppressionRule:
    """Test SuppressionRule functionality"""
    
    def test_suppression_rule_creation(self):
        """Test creating suppression rules"""
        now = datetime.now()
        rule = SuppressionRule(
            pattern="test_pattern",
            duration_minutes=30,
            reason="Test reason",
            created_at=now,
            expires_at=now + timedelta(minutes=30)
        )
        
        assert rule.pattern == "test_pattern"
        assert rule.duration_minutes == 30
        assert rule.reason == "Test reason"
        assert rule.is_active()
    
    def test_suppression_rule_expiry(self):
        """Test suppression rule expiry"""
        past_time = datetime.now() - timedelta(minutes=60)
        rule = SuppressionRule(
            pattern="test_pattern",
            duration_minutes=30,
            reason="Test reason",
            created_at=past_time,
            expires_at=past_time + timedelta(minutes=30)  # Expired
        )
        
        assert not rule.is_active()
    
    def test_matches_alert_by_title(self):
        """Test alert matching by title"""
        rule = SuppressionRule(
            pattern="collection rate",
            duration_minutes=30,
            reason="Test",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(minutes=30)
        )
        
        alert = Alert(
            alert_id="test_001",
            rule_id="test_rule",
            timestamp=datetime.now(),
            severity="warning",
            title="Collection Rate Below Threshold",
            message="Rate is low",
            affected_components=[],
            current_value=5,
            threshold_value=10,
            metrics_context={},
            recommended_actions=[],
            status="active"
        )
        
        assert rule.matches_alert(alert)
    
    def test_matches_alert_by_message(self):
        """Test alert matching by message"""
        rule = SuppressionRule(
            pattern="rate is low",
            duration_minutes=30,
            reason="Test",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(minutes=30)
        )
        
        alert = Alert(
            alert_id="test_001",
            rule_id="test_rule",
            timestamp=datetime.now(),
            severity="warning",
            title="Test Alert",
            message="Collection rate is low",
            affected_components=[],
            current_value=5,
            threshold_value=10,
            metrics_context={},
            recommended_actions=[],
            status="active"
        )
        
        assert rule.matches_alert(alert)
    
    def test_matches_alert_by_rule_id(self):
        """Test alert matching by rule ID"""
        rule = SuppressionRule(
            pattern="collection_rate_low",
            duration_minutes=30,
            reason="Test",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(minutes=30)
        )
        
        alert = Alert(
            alert_id="test_001",
            rule_id="collection_rate_low",
            timestamp=datetime.now(),
            severity="warning",
            title="Different Title",
            message="Different message",
            affected_components=[],
            current_value=5,
            threshold_value=10,
            metrics_context={},
            recommended_actions=[],
            status="active"
        )
        
        assert rule.matches_alert(alert)
    
    def test_no_match_when_expired(self):
        """Test that expired rules don't match"""
        past_time = datetime.now() - timedelta(minutes=60)
        rule = SuppressionRule(
            pattern="test",
            duration_minutes=30,
            reason="Test",
            created_at=past_time,
            expires_at=past_time + timedelta(minutes=30)  # Expired
        )
        
        alert = Alert(
            alert_id="test_001",
            rule_id="test_rule",
            timestamp=datetime.now(),
            severity="warning",
            title="Test Alert",
            message="Test message",
            affected_components=[],
            current_value=5,
            threshold_value=10,
            metrics_context={},
            recommended_actions=[],
            status="active"
        )
        
        assert not rule.matches_alert(alert)


class TestSuppressionRuleManager:
    """Test SuppressionRuleManager functionality"""
    
    @pytest.fixture
    def rule_manager(self):
        """Create test suppression rule manager"""
        suppression_manager = AlertSuppressionManager()
        return SuppressionRuleManager(suppression_manager)
    
    def test_analyze_and_suppress_burst(self, rule_manager):
        """Test burst detection and suppression"""
        # Create multiple similar alerts to trigger burst suppression
        for i in range(6):  # More than burst threshold (5)
            alert = Alert(
                alert_id=f"test_alert_{i}",
                rule_id="test_rule",
                timestamp=datetime.now(),
                severity="warning",
                title=f"Test Alert {i}",
                message=f"Test message {i}",
                affected_components=[],
                current_value=i,
                threshold_value=10,
                metrics_context={},
                recommended_actions=[],
                status="active"
            )
            
            # Should create suppression rule on the 5th alert
            created_rule = rule_manager.analyze_and_suppress(alert)
            if i == 4:  # 5th alert (0-indexed)
                assert created_rule is True
            else:
                assert created_rule is False
    
    def test_get_suppression_recommendations(self, rule_manager):
        """Test getting suppression recommendations"""
        # Create recent alerts that should trigger recommendations
        recent_alerts = []
        base_time = datetime.now()
        
        # Create 4 similar alerts within an hour
        for i in range(4):
            alert = Alert(
                alert_id=f"test_alert_{i}",
                rule_id="frequent_rule",
                timestamp=base_time - timedelta(minutes=i*10),
                severity="error",
                title=f"Frequent Alert {i}",
                message=f"This happens often {i}",
                affected_components=[],
                current_value=i,
                threshold_value=5,
                metrics_context={},
                recommended_actions=[],
                status="active"
            )
            recent_alerts.append(alert)
        
        recommendations = rule_manager.get_suppression_recommendations(recent_alerts)
        
        assert len(recommendations) > 0
        
        recommendation = recommendations[0]
        assert recommendation['pattern'] == "frequent_rule_error"
        assert recommendation['alert_count'] == 4
        assert recommendation['confidence'] in ['high', 'medium', 'low']
    
    def test_create_maintenance_suppression(self, rule_manager):
        """Test creating maintenance suppression"""
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=2)
        
        rule_manager.create_maintenance_suppression(
            component="database",
            start_time=start_time,
            end_time=end_time,
            reason="Scheduled database maintenance"
        )
        
        # Should have created a suppression rule
        active = rule_manager.suppression_manager.get_active_suppressions()
        assert len(active) > 0
        
        rule = active[0]
        assert "database" in rule['pattern']
        assert "maintenance" in rule['reason']