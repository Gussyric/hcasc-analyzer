#!/bin/bash
# Download all 2025 HCASC NCT PDFs
# Run from anywhere — files saved to ~/Downloads/nct-2025/

mkdir -p ~/Downloads/nct-2025/scoresheets
mkdir -p ~/Downloads/nct-2025/summary

BASE="https://www.hcasc.com"

echo "Downloading summary PDFs..."

curl -L -o ~/Downloads/nct-2025/summary/TeamStatsRoundRobin.pdf       "$BASE/nct25/TeamStatsRoundRobin.pdf"
curl -L -o ~/Downloads/nct-2025/summary/RoundRobinResults.pdf         "$BASE/nct25/RoundRobinResults.pdf"
curl -L -o ~/Downloads/nct-2025/summary/RoundRobinResultsAgainstCompetitors.pdf "$BASE/nct25/RoundRobinResultsAgainstCompetitors.pdf"
curl -L -o ~/Downloads/nct-2025/summary/RoundRobinScoresByDivision.pdf "$BASE/nct25/RoundRobinScoresByDivision.pdf"
curl -L -o ~/Downloads/nct-2025/summary/PlayoffPlayerStats.pdf        "$BASE/nct25/PlayoffPlayerStats.pdf"
curl -L -o ~/Downloads/nct-2025/summary/PlayoffTeamResults.pdf        "$BASE/nct25/PlayoffTeamResults.pdf"
curl -L -o ~/Downloads/nct-2025/summary/PlayoffScoresheets.pdf        "$BASE/nct25/PlayOffs_Scoresheets.pdf"

echo "Downloading division scoresheets..."

curl -L -o ~/Downloads/nct-2025/scoresheets/Black_Division_Scoresheets.pdf   "$BASE/BlackDivisionRR_Scoresheets.pdf"
curl -L -o ~/Downloads/nct-2025/scoresheets/Blue_Division_Scoresheets.pdf    "$BASE/BlueDivisionRR_Scoresheets.pdf"
curl -L -o ~/Downloads/nct-2025/scoresheets/Brown_Division_Scoresheets.pdf   "$BASE/BrownDivisionRR_Scoresheets.pdf"
curl -L -o ~/Downloads/nct-2025/scoresheets/Green_Division_Scoresheets.pdf   "$BASE/GreenDivisionRR_Scoresheets.pdf"
curl -L -o ~/Downloads/nct-2025/scoresheets/Orange_Division_Scoresheets.pdf  "$BASE/OrangeDivisionRR_Scoresheets.pdf"
curl -L -o ~/Downloads/nct-2025/scoresheets/Purple_Division_Scoresheets.pdf  "$BASE/PurpleDivisionRR_Scoresheets.pdf"
curl -L -o ~/Downloads/nct-2025/scoresheets/Red_Division_Scoresheets.pdf     "$BASE/RedDivisionRR_Scoresheets.pdf"
curl -L -o ~/Downloads/nct-2025/scoresheets/Yellow_Division_Scoresheets.pdf  "$BASE/YellowDivisionRR_Scoresheets.pdf"

echo ""
echo "Done. Files saved to ~/Downloads/nct-2025/"
echo ""
echo "Summary PDFs:"
ls ~/Downloads/nct-2025/summary/
echo ""
echo "Scoresheets:"
ls ~/Downloads/nct-2025/scoresheets/
