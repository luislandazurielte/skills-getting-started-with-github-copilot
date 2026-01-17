"""
Test suite for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state after each test"""
    # Store original state
    original_activities = {
        name: {
            **details,
            "participants": details["participants"].copy()
        }
        for name, details in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for name, details in original_activities.items():
        activities[name]["participants"] = details["participants"].copy()


class TestGetActivities:
    """Tests for GET /activities endpoint"""

    def test_get_activities_success(self, client):
        """Test retrieving all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        
        # Verify it's a dictionary
        assert isinstance(data, dict)
        
        # Verify expected activities exist
        assert "Basketball Team" in data
        assert "Tennis Club" in data
        assert "Art Studio" in data
        
        # Verify activity structure
        activity = data["Basketball Team"]
        assert "description" in activity
        assert "schedule" in activity
        assert "max_participants" in activity
        assert "participants" in activity
        assert isinstance(activity["participants"], list)

    def test_activities_have_initial_participants(self, client):
        """Test that activities have initial participants"""
        response = client.get("/activities")
        data = response.json()
        
        # Check a few activities have participants
        assert len(data["Basketball Team"]["participants"]) > 0
        assert len(data["Art Studio"]["participants"]) > 0


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_success(self, client, reset_activities):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Basketball%20Team/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        
        # Verify participant was added
        assert "newstudent@mergington.edu" in activities["Basketball Team"]["participants"]

    def test_signup_nonexistent_activity(self, client, reset_activities):
        """Test signup for a non-existent activity"""
        response = client.post(
            "/activities/Nonexistent%20Club/signup",
            params={"email": "student@mergington.edu"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_signup_duplicate_student(self, client, reset_activities):
        """Test signup fails when student is already registered"""
        # alex@mergington.edu is already in Basketball Team
        response = client.post(
            "/activities/Basketball%20Team/signup",
            params={"email": "alex@mergington.edu"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]

    def test_signup_multiple_students(self, client, reset_activities):
        """Test multiple different students can signup for same activity"""
        email1 = "student1@mergington.edu"
        email2 = "student2@mergington.edu"
        
        response1 = client.post(
            "/activities/Tennis%20Club/signup",
            params={"email": email1}
        )
        response2 = client.post(
            "/activities/Tennis%20Club/signup",
            params={"email": email2}
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert email1 in activities["Tennis Club"]["participants"]
        assert email2 in activities["Tennis Club"]["participants"]


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""

    def test_unregister_success(self, client, reset_activities):
        """Test successful unregister from an activity"""
        # alex@mergington.edu is in Basketball Team
        response = client.delete(
            "/activities/Basketball%20Team/unregister",
            params={"email": "alex@mergington.edu"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "Removed" in data["message"]
        
        # Verify participant was removed
        assert "alex@mergington.edu" not in activities["Basketball Team"]["participants"]

    def test_unregister_nonexistent_activity(self, client, reset_activities):
        """Test unregister from a non-existent activity"""
        response = client.delete(
            "/activities/Nonexistent%20Club/unregister",
            params={"email": "student@mergington.edu"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_unregister_student_not_registered(self, client, reset_activities):
        """Test unregister fails when student is not registered"""
        response = client.delete(
            "/activities/Basketball%20Team/unregister",
            params={"email": "notregistered@mergington.edu"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "not signed up" in data["detail"]

    def test_unregister_then_signup_again(self, client, reset_activities):
        """Test student can signup again after unregistering"""
        email = "student@mergington.edu"
        activity = "Tennis%20Club"
        
        # Signup
        signup_response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert signup_response.status_code == 200
        
        # Unregister
        unregister_response = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        assert unregister_response.status_code == 200
        
        # Signup again
        signup_again_response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert signup_again_response.status_code == 200


class TestActivityCapacity:
    """Tests for activity capacity management"""

    def test_signup_respects_capacity(self, client, reset_activities):
        """Test that we can track participant count"""
        response = client.get("/activities")
        data = response.json()
        
        activity = data["Tennis Club"]
        participants_count = len(activity["participants"])
        max_capacity = activity["max_participants"]
        
        assert participants_count <= max_capacity


class TestIntegration:
    """Integration tests for the full workflow"""

    def test_complete_workflow(self, client, reset_activities):
        """Test complete signup and unregister workflow"""
        email = "integration@mergington.edu"
        activity = "Chess%20Club"
        
        # Get initial state
        response1 = client.get("/activities")
        initial_participants = len(response1.json()["Chess Club"]["participants"])
        
        # Signup
        response2 = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert response2.status_code == 200
        
        # Verify signup
        response3 = client.get("/activities")
        after_signup = len(response3.json()["Chess Club"]["participants"])
        assert after_signup == initial_participants + 1
        assert email in response3.json()["Chess Club"]["participants"]
        
        # Unregister
        response4 = client.delete(
            f"/activities/{activity}/unregister",
            params={"email": email}
        )
        assert response4.status_code == 200
        
        # Verify unregister
        response5 = client.get("/activities")
        after_unregister = len(response5.json()["Chess Club"]["participants"])
        assert after_unregister == initial_participants
        assert email not in response5.json()["Chess Club"]["participants"]
