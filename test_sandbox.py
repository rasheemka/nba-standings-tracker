"""
Test script to verify the sandbox mode API endpoints
"""

import requests
import json

BASE_URL = "http://localhost:5001"

def test_get_teams():
    """Test the /api/teams endpoint"""
    print("\n=== Testing /api/teams endpoint ===")
    response = requests.get(f"{BASE_URL}/api/teams")
    data = response.json()
    
    if data['status'] == 'success':
        print(f"✓ Found {len(data['teams'])} teams")
        print(f"✓ Current assignments for {len(data['current_assignments'])} people")
        return data['current_assignments'], data['teams']
    else:
        print("✗ Failed to get teams")
        return None, None

def test_recalculate(custom_assignments):
    """Test the /api/recalculate endpoint"""
    print("\n=== Testing /api/recalculate endpoint ===")
    
    response = requests.post(
        f"{BASE_URL}/api/recalculate",
        json={'team_assignments': custom_assignments},
        headers={'Content-Type': 'application/json'}
    )
    
    data = response.json()
    
    if data['status'] == 'success':
        print("✓ Recalculation successful")
        print("\nUpdated standings:")
        for rank, (friend, stats) in enumerate(data['sorted_friends'], 1):
            print(f"  {rank}. {friend}: {stats['total_wins']} wins ({stats['win_pct']*100:.1f}%)")
        return True
    else:
        print(f"✗ Recalculation failed: {data.get('message', 'Unknown error')}")
        return False

def main():
    print("NBA Standings Tracker - Sandbox Mode Test")
    print("=" * 50)
    
    # Test 1: Get current teams and assignments
    assignments, all_teams = test_get_teams()
    
    if not assignments or not all_teams:
        print("\n❌ Cannot proceed without team data. Make sure the server is running.")
        return
    
    print("\nOriginal assignments:")
    for friend, teams in assignments.items():
        print(f"  {friend}: {', '.join(teams)}")
    
    # Test 2: Create a custom assignment (swap some teams around)
    custom = assignments.copy()
    
    # Example: Give JJ some different teams
    if 'JJ' in custom and len(all_teams) >= 4:
        print("\n=== Creating custom scenario ===")
        print(f"Changing JJ's teams from {custom['JJ']} to first 4 teams in list")
        custom['JJ'] = all_teams[:4]
        
        # Swap another person's teams too
        if 'Nick' in custom and len(all_teams) >= 8:
            print(f"Changing Nick's teams from {custom['Nick']} to teams 4-7")
            custom['Nick'] = all_teams[4:8]
    
    # Test 3: Recalculate with custom assignments
    success = test_recalculate(custom)
    
    if success:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed")

if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Cannot connect to server.")
        print("Make sure the web app is running on http://localhost:5001")
        print("Run: python web_app.py")
