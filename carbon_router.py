import random
from datetime import datetime
from github import Github
import yaml
import base64

# --- 1. CONFIGURATION ---
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "YOUR_TOKEN_GOES_HERE_LOCALLY")
REPO_NAME = "SUYOGGAMPAWAR/Carbon-Aware-Workload-Orchestrator" # e.g., suyoggampawar/greenops-workload

REGIONS = {
    "us-east": {"name": "Virginia", "base_emissions": 450, "path": "us-east/deployment.yaml"},   
    "india": {"name": "Maharashtra", "base_emissions": 500, "path": "india/deployment.yaml"}       
}

# --- 2. THE GITHUB UPDATER (The "Hands") ---
def update_github_replicas(repo, file_path, new_replica_count):
    """Pulls the deployment.yaml, changes the replica count, and pushes it back."""
    file_contents = repo.get_contents(file_path)
    decoded_content = base64.b64decode(file_contents.content).decode('utf-8')
    
    # Parse the YAML, update replicas, and turn it back into a string
    yaml_data = yaml.safe_load(decoded_content)
    if yaml_data['spec']['replicas'] == new_replica_count:
        return # Skip if it's already set to the right number
        
    yaml_data['spec']['replicas'] = new_replica_count
    new_yaml_string = yaml.dump(yaml_data, default_flow_style=False)
    
    # Commit the change
    repo.update_file(
        path=file_path,
        message=f"GreenOps Auto-Scaler: Shifting replicas to {new_replica_count} in {file_path}",
        content=new_yaml_string,
        sha=file_contents.sha
    )
    print(f"[*] Successfully updated {file_path} to {new_replica_count} replicas.")

# --- 3. THE MOCK API ---
def get_mock_carbon_intensity(region_key):
    base = REGIONS[region_key]["base_emissions"]
    hour = datetime.now().hour
    if 10 <= hour <= 16:
        time_modifier = random.randint(-150, -50)
    else:
        time_modifier = random.randint(50, 150)
    fluctuation = random.randint(-25, 25)
    return max(100, base + time_modifier + fluctuation) 

# --- 4. THE ORCHESTRATOR LOGIC ---
def main():
    print("Initiating GreenOps Carbon Routing Protocol...\n")
    
    # Connect to GitHub
    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(REPO_NAME)
    
    us_emissions = get_mock_carbon_intensity("us-east")
    india_emissions = get_mock_carbon_intensity("india")
    
    print(f"Current US-East Emissions: {us_emissions} gCO2eq/kWh")
    print(f"Current India Emissions:   {india_emissions} gCO2eq/kWh")
    
    if india_emissions < us_emissions:
        print("\n=> DECISION: Shifting workload to region-india")
        update_github_replicas(repo, REGIONS["us-east"]["path"], 0) # Turn US off
        update_github_replicas(repo, REGIONS["india"]["path"], 3)   # Turn India on
    else:
        print("\n=> DECISION: Maintaining workload in region-us-east")
        update_github_replicas(repo, REGIONS["india"]["path"], 0)   # Turn India off
        update_github_replicas(repo, REGIONS["us-east"]["path"], 3) # Turn US on

if __name__ == "__main__":
    main()
