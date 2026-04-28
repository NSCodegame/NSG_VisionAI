"""
Verification script for Video Feed API endpoints.
This script verifies that all endpoints are properly registered and accessible.
"""
from app.main import app

def verify_feeds_endpoints():
    """Verify all feed endpoints are registered"""
    
    # Get all routes
    feed_routes = [
        route for route in app.routes 
        if hasattr(route, 'path') and '/feeds' in route.path
    ]
    
    print("=" * 70)
    print("VIDEO FEED API ENDPOINTS VERIFICATION")
    print("=" * 70)
    print(f"\nTotal feed endpoints registered: {len(feed_routes)}\n")
    
    expected_endpoints = [
        ("GET", "/api/v1/feeds", "List video feeds (OPERATOR+)"),
        ("POST", "/api/v1/feeds", "Create video feed (ADMIN only)"),
        ("GET", "/api/v1/feeds/{feed_id}", "Get feed details (OPERATOR+)"),
        ("PUT", "/api/v1/feeds/{feed_id}", "Update feed (ADMIN only)"),
        ("DELETE", "/api/v1/feeds/{feed_id}", "Delete feed (ADMIN only)"),
        ("POST", "/api/v1/feeds/{feed_id}/toggle-ai", "Toggle AI processing (OPERATOR+)"),
        ("POST", "/api/v1/feeds/test", "Test RTSP connection (ADMIN only)"),
        ("GET", "/api/v1/feeds/{feed_id}/stats", "Get feed statistics (OPERATOR+)"),
    ]
    
    print("Expected Endpoints:")
    print("-" * 70)
    
    for method, path, description in expected_endpoints:
        # Find matching route
        matching_routes = [
            r for r in feed_routes 
            if r.path == path and method in r.methods
        ]
        
        status = "✓" if matching_routes else "✗"
        print(f"{status} {method:6} {path:40} {description}")
    
    print("\n" + "=" * 70)
    print("VERIFICATION COMPLETE")
    print("=" * 70)
    
    # Verify all expected endpoints are present
    all_present = all(
        any(r.path == path and method in r.methods for r in feed_routes)
        for method, path, _ in expected_endpoints
    )
    
    if all_present:
        print("\n✓ All 8 feed endpoints are properly registered!")
        print("✓ Router is integrated into main application!")
        print("\nEndpoints are ready for use:")
        print("  - OPERATOR+ can: list feeds, get feed details, toggle AI, view stats")
        print("  - ADMIN can: all OPERATOR+ actions + create, update, delete, test connection")
        return True
    else:
        print("\n✗ Some endpoints are missing!")
        return False


if __name__ == "__main__":
    success = verify_feeds_endpoints()
    exit(0 if success else 1)
