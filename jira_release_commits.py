#!/usr/bin/env python3
"""
JIRA Release Commit Extractor

This script retrieves all tasks that had development done within a specified JIRA release,
retrieves all merged request commit IDs for those tickets, orders the commits from oldest
to newest, and prepares a bash script that will iterate over those commits and cherry-pick
them to a release branch.

Usage:
    python jira_release_commits.py --release-id <release_id> --target-branch <target_branch> [--output <output_file>]

Example:
    python jira_release_commits.py --release-id 1234 --target-branch release/v1.0 --output cherry_pick_script.sh
"""

import argparse
import os
import sys
import json
import requests
from datetime import datetime
from git import Repo, Git
import re

class JiraReleaseCommitExtractor:
    def __init__(self, release_id, target_branch, output_file=None):
        """
        Initialize the JIRA Release Commit Extractor.

        Args:
            release_id (str): The JIRA release ID.
            target_branch (str): The target branch for cherry-picking.
            output_file (str, optional): The output file for the bash script. Defaults to None.
        """
        self.release_id = release_id
        self.target_branch = target_branch
        self.output_file = output_file or f"cherry_pick_release_{release_id}.sh"

        # JIRA API configuration
        self.jira_base_url = os.environ.get('JIRA_BASE_URL', 'https://your-jira-instance.atlassian.net')
        self.jira_username = os.environ.get('JIRA_USERNAME')
        self.jira_api_token = os.environ.get('JIRA_API_TOKEN')

        if not self.jira_username or not self.jira_api_token:
            print("Error: JIRA_USERNAME and JIRA_API_TOKEN environment variables must be set.")
            sys.exit(1)

        # Git repository configuration
        self.repo_path = os.getcwd()  # Current directory
        try:
            self.repo = Repo(self.repo_path)
            self.git = Git(self.repo_path)
        except Exception as e:
            print(f"Error initializing Git repository: {e}")
            sys.exit(1)

    def get_release_info(self):
        """
        Get information about the JIRA release.

        Returns:
            dict: The release information.
        """
        url = f"{self.jira_base_url}/rest/api/2/version/{self.release_id}"
        response = self._make_jira_request(url)
        return response

    def get_tasks_in_release(self):
        """
        Get all tasks that had development done within the specified JIRA release.

        Returns:
            list: A list of JIRA issue objects.
        """
        # Get the release name first
        release_info = self.get_release_info()
        release_name = release_info.get('name')

        if not release_name:
            print(f"Error: Could not find release with ID {self.release_id}")
            sys.exit(1)

        print(f"Found release: {release_name}")

        # JQL query to find all issues in the release
        jql = f'fixVersion = "{release_name}" ORDER BY created ASC'
        url = f"{self.jira_base_url}/rest/api/2/search"

        # Initialize variables for pagination
        all_issues = []
        start_at = 0
        max_results = 100  # JIRA API typically limits to 100 records per request
        total = None

        # Loop until we've retrieved all issues
        while total is None or start_at < total:
            params = {
                'jql': jql,
                'fields': 'key,summary,status,created,updated',
                'maxResults': max_results,
                'startAt': start_at
            }

            response = self._make_jira_request(url, params=params)
            issues = response.get('issues', [])

            if not issues:
                break

            all_issues.extend(issues)

            # Update pagination variables
            if total is None:
                total = response.get('total', 0)

            start_at += len(issues)

            print(f"Retrieved {len(issues)} issues (total so far: {len(all_issues)} of {total})")

            # If we got fewer issues than requested, we've reached the end
            if len(issues) < max_results:
                break

        print(f"Found {len(all_issues)} issues in release {release_name}")
        return all_issues

    def get_commit_ids_for_tickets(self, issues):
        """
        Get all commit IDs associated with the given JIRA tickets.

        Args:
            issues (list): A list of JIRA issue objects.

        Returns:
            list: A list of commit objects with ticket keys and commit hashes.
        """
        commits = []
        unique_commit_hashes = set()  # Track unique commit hashes

        # Get all commit messages
        all_commits = list(self.repo.iter_commits())

        # Extract ticket keys from issues
        ticket_keys = [issue['key'] for issue in issues]

        # Find commits that reference the ticket keys
        for commit in all_commits:
            commit_message = commit.message
            commit_hash = commit.hexsha

            # Check if any ticket key is in the commit message
            for ticket_key in ticket_keys:
                if re.search(rf'(?<!\w){ticket_key}(?!\d)', commit_message, re.IGNORECASE):

                    # Skip if we've already processed this commit
                    if commit_hash in unique_commit_hashes:
                        continue

                    commits.append({
                        'ticket_key': ticket_key,
                        'commit_hash': commit_hash,
                        'commit_date': datetime.fromtimestamp(commit.committed_date),
                        'commit_message': commit_message.strip()
                    })
                    unique_commit_hashes.add(commit_hash)  # Mark this commit as processed

        print(f"Found {len(commits)} unique commits associated with the tickets")
        return commits

    def order_commits_chronologically(self, commits):
        """
        Order the commits from oldest to newest.

        Args:
            commits (list): A list of commit objects.

        Returns:
            list: A list of commit objects ordered by commit date.
        """
        return sorted(commits, key=lambda x: x['commit_date'])

    def generate_cherry_pick_script(self, ordered_commits):
        """
        Generate a bash script to cherry-pick the commits.

        Args:
            ordered_commits (list): A list of commit objects ordered by commit date.

        Returns:
            str: The path to the generated bash script.
        """
        script_content = [
            "#!/bin/bash",
            "",
            f"# Cherry-pick script for JIRA release {self.release_id}",
            f"# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "# Exit on error",
            "set -e",
            "",
            f"# Checkout the target branch",
            f"git checkout {self.target_branch}",
            "",
            "# Cherry-pick each commit",
            ""
        ]

        for commit in ordered_commits:
            script_content.append(f"# {commit['ticket_key']}: {commit['commit_message'].split(chr(10))[0]}")
            script_content.append(f"git cherry-pick --strategy=recursive -X theirs {commit['commit_hash']}")
            script_content.append("")

        script_content.append("echo 'Cherry-picking completed successfully!'")

        # Write the script to a file
        with open(self.output_file, 'w') as f:
            f.write('\n'.join(script_content))

        # Make the script executable
        os.chmod(self.output_file, 0o755)

        print(f"Cherry-pick script generated: {self.output_file}")
        return self.output_file

    def _make_jira_request(self, url, params=None):
        """
        Make a request to the JIRA API.

        Args:
            url (str): The URL to request.
            params (dict, optional): Query parameters. Defaults to None.

        Returns:
            dict: The JSON response.
        """
        auth = (self.jira_username, self.jira_api_token)
        headers = {'Content-Type': 'application/json'}

        try:
            response = requests.get(url, auth=auth, headers=headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error making request to JIRA API: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Response status code: {e.response.status_code}")
                print(f"Response body: {e.response.text}")
            sys.exit(1)

    def run(self):
        """
        Run the JIRA Release Commit Extractor.

        Returns:
            str: The path to the generated bash script.
        """
        print(f"Starting JIRA Release Commit Extractor for release ID: {self.release_id}")

        # Step 1: Get all tasks in the release
        issues = self.get_tasks_in_release()

        # Step 2: Get all commit IDs for the tickets
        commits = self.get_commit_ids_for_tickets(issues)

        # Step 3: Order the commits chronologically
        ordered_commits = self.order_commits_chronologically(commits)

        # Step 4: Generate the cherry-pick script
        script_path = self.generate_cherry_pick_script(ordered_commits)

        print(f"JIRA Release Commit Extractor completed successfully!")
        return script_path

def main():
    parser = argparse.ArgumentParser(description='JIRA Release Commit Extractor')
    parser.add_argument('--release-id', required=True, help='JIRA release ID')
    parser.add_argument('--target-branch', required=True, help='Target branch for cherry-picking')
    parser.add_argument('--output', help='Output file for the bash script')

    args = parser.parse_args()

    extractor = JiraReleaseCommitExtractor(
        release_id=args.release_id,
        target_branch=args.target_branch,
        output_file=args.output
    )

    extractor.run()

if __name__ == '__main__':
    main()