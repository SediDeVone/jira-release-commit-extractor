# JIRA Release Commit Extractor

This script retrieves all tasks that had development done within a specified JIRA release, retrieves all merged request commit IDs for those tickets, orders the commits from oldest to newest, and prepares a bash script that will iterate over those commits and cherry-pick them to a release branch.

## Prerequisites

- Python 3.6 or higher
- Git repository with commit messages that reference JIRA ticket keys
- JIRA account with API access

## Installation

1. Clone this repository
2. Install the required dependencies:

```bash
pip install requests gitpython
```

## Configuration

The script requires the following environment variables to be set:

- `JIRA_BASE_URL`: The base URL of your JIRA instance (e.g., `https://your-company.atlassian.net`)
- `JIRA_USERNAME`: Your JIRA username (usually your email address)
- `JIRA_API_TOKEN`: Your JIRA API token (can be generated in your Atlassian account settings)

You can set these environment variables in your shell:

```bash
export JIRA_BASE_URL="https://your-company.atlassian.net"
export JIRA_USERNAME="your-email@example.com"
export JIRA_API_TOKEN="your-api-token"
```

Or you can create a `.env` file and use a package like `python-dotenv` to load them.

## Usage

```bash
python jira_release_commits.py --release-id <release_id> --target-branch <target_branch> [--output <output_file>]
```

### Arguments

- `--release-id`: The JIRA release ID (required)
- `--target-branch`: The target branch for cherry-picking (required)
- `--output`: The output file for the bash script (optional, defaults to `cherry_pick_release_<release_id>.sh`)

### Example

```bash
python jira_release_commits.py --release-id 1234 --target-branch release/v1.0 --output cherry_pick_script.sh
```

This will:
1. Connect to your JIRA instance
2. Retrieve all tasks in release with ID 1234
3. Find all commits in your Git repository that reference those tasks
4. Order the commits chronologically
5. Generate a bash script called `cherry_pick_script.sh` that will cherry-pick those commits to the `release/v1.0` branch

## Running the Generated Script

After the script is generated, you can run it to perform the cherry-picking:

```bash
./cherry_pick_script.sh
```

The script includes error handling (`set -e`) to stop if any cherry-pick fails.

## How It Works

1. **Retrieving Tasks**: The script uses the JIRA API to get all issues in the specified release.
2. **Finding Commits**: It scans the Git repository for commits that reference the JIRA ticket keys.
3. **Ordering Commits**: The commits are sorted by their commit date from oldest to newest.
4. **Generating Script**: A bash script is created with commands to cherry-pick each commit to the target branch.

## Troubleshooting

- **JIRA API Errors**: Make sure your environment variables are set correctly and that your API token has the necessary permissions.
- **Git Repository Errors**: The script must be run from within a Git repository.
- **Cherry-Pick Conflicts**: If the generated script encounters conflicts during cherry-picking, it will stop. You'll need to resolve the conflicts manually and continue.

## License

This project is licensed under the MIT License - see the LICENSE file for details.