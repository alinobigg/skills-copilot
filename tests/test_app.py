"""
Tests for the Mergington High School Activities API
"""

import pytest
import sys
from pathlib import Path

# Add src directory to path so we can import app
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastapi.testclient import TestClient
from app import app, activities

client = TestClient(app)


class TestRoot:
    """Tests for the root endpoint"""

    def test_root_redirects_to_static_index(self):
        """Test that root endpoint redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for the GET /activities endpoint"""

    def test_get_activities(self):
        """Test that we can retrieve all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "Chess Club" in data
        assert "Programming Class" in data

    def test_activities_have_required_fields(self):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        data = response.json()
        for activity_name, activity_details in data.items():
            assert "description" in activity_details
            assert "schedule" in activity_details
            assert "max_participants" in activity_details
            assert "participants" in activity_details
            assert isinstance(activity_details["participants"], list)


class TestSignup:
    """Tests for the POST /activities/{activity_name}/signup endpoint"""

    def test_signup_success(self):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]

    def test_signup_activity_not_found(self):
        """Test signup for non-existent activity"""
        response = client.post(
            "/activities/Non Existent Club/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_signup_duplicate_student(self):
        """Test that a student cannot sign up twice for the same activity"""
        email = "michael@mergington.edu"  # Already in Chess Club
        response = client.post(
            f"/activities/Chess Club/signup?email={email}"
        )
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]

    def test_signup_adds_participant(self):
        """Test that signup actually adds the participant to the activity"""
        test_email = "testsignup@mergington.edu"
        # First signup
        response = client.post(
            f"/activities/Art Studio/signup?email={test_email}"
        )
        assert response.status_code == 200
        
        # Verify the participant was added
        activities_response = client.get("/activities")
        data = activities_response.json()
        assert test_email in data["Art Studio"]["participants"]


class TestUnregister:
    """Tests for the DELETE /activities/{activity_name}/unregister endpoint"""

    def test_unregister_success(self):
        """Test successful unregister from an activity"""
        email = "testunregister@mergington.edu"
        
        # First, sign up
        client.post(f"/activities/Drama Club/signup?email={email}")
        
        # Then unregister
        response = client.delete(
            f"/activities/Drama Club/unregister?email={email}"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Removed" in data["message"]

    def test_unregister_activity_not_found(self):
        """Test unregister for non-existent activity"""
        response = client.delete(
            "/activities/Non Existent Club/unregister?email=student@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]

    def test_unregister_participant_not_found(self):
        """Test unregister for non-existent participant"""
        response = client.delete(
            "/activities/Tennis Club/unregister?email=nonexistent@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Participant not found" in data["detail"]

    def test_unregister_removes_participant(self):
        """Test that unregister actually removes the participant"""
        email = "testunregister2@mergington.edu"
        
        # Sign up
        client.post(f"/activities/Debate Team/signup?email={email}")
        
        # Verify participant is there
        activities_response = client.get("/activities")
        data = activities_response.json()
        assert email in data["Debate Team"]["participants"]
        
        # Unregister
        client.delete(f"/activities/Debate Team/unregister?email={email}")
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        data = activities_response.json()
        assert email not in data["Debate Team"]["participants"]


class TestIntegration:
    """Integration tests"""

    def test_signup_and_unregister_flow(self):
        """Test the full flow of signing up and then unregistering"""
        email = "integrationtest@mergington.edu"
        activity = "Science Club"
        
        # Get initial state
        initial_response = client.get("/activities")
        initial_data = initial_response.json()
        initial_participant_count = len(initial_data[activity]["participants"])
        
        # Sign up
        signup_response = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        assert signup_response.status_code == 200
        
        # Verify participant was added
        after_signup_response = client.get("/activities")
        after_signup_data = after_signup_response.json()
        assert len(after_signup_data[activity]["participants"]) == initial_participant_count + 1
        assert email in after_signup_data[activity]["participants"]
        
        # Unregister
        unregister_response = client.delete(
            f"/activities/{activity}/unregister?email={email}"
        )
        assert unregister_response.status_code == 200
        
        # Verify participant was removed
        final_response = client.get("/activities")
        final_data = final_response.json()
        assert len(final_data[activity]["participants"]) == initial_participant_count
        assert email not in final_data[activity]["participants"]
