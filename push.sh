#!/bin/bash
# LeadOS — Push war room build to GitHub
# Run this once from your local machine or Railway shell

echo "Pushing LeadOS war room build..."
git remote set-url origin https://$GITHUB_TOKEN@github.com/enriquescdo-max/Tryleados.git
git push origin main
echo "Done. Railway will auto-deploy backend. Netlify will auto-deploy frontend."
