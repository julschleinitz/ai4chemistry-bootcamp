/**
 * Molecular Generation tutorial -- leaderboard Web App endpoint.
 *
 * Unlike the pretraining_finetuning leaderboard, students never self-report a score. This endpoint
 * dispatches on an `action` field in the POST payload:
 *   - action "submit"       -- a student's notebook posts one SMILES; appended to "Submissions".
 *   - action "record_score" -- score_submissions.py (instructor-run, see SETUP.md) posts a graded
 *                               result (real docking at exhaustiveness=8/num_modes=10, plus
 *                               QED/toxicity alerts); appended to "Leaderboard".
 * The tutorial page's live leaderboard widget only ever reads the "Leaderboard" tab.
 *
 * ONE-TIME SETUP (see SETUP.md)
 * 1. Create a Google Sheet with two tabs: "Submissions" (header = submissions_schema.csv) and
 *    "Leaderboard" (header = results_schema.csv).
 * 2. Extensions -> Apps Script, paste this file in.
 * 3. Deploy -> New deployment -> type "Web app" -> execute as "Me" -> who has access "Anyone".
 * 4. Copy the deployment URL into the notebook's LEADERBOARD_ENDPOINT_URL constant and into
 *    score_submissions.py's LEADERBOARD_ENDPOINT_URL.
 */

const SUBMISSIONS_SHEET_NAME = 'Submissions';
const LEADERBOARD_SHEET_NAME = 'Leaderboard';

const SUBMISSIONS_COLUMNS = ['run_id', 'timestamp_utc', 'team_name', 'smiles', 'method_family', 'notes'];

const LEADERBOARD_COLUMNS = [
  'run_id', 'timestamp_utc_submitted', 'timestamp_utc_scored', 'team_name', 'smiles',
  'best_affinity_kcal_mol', 'qed', 'toxicity_alerts', 'exhaustiveness', 'num_modes', 'pose_sdf',
  'pocket_pdb_id', 'notebook_version', 'notes',
];

function doPost(e) {
  try {
    const payload = JSON.parse(e.postData.contents);
    const action = payload.action;

    if (action === 'submit') {
      return appendRow_(SUBMISSIONS_SHEET_NAME, SUBMISSIONS_COLUMNS, payload);
    }
    if (action === 'record_score') {
      return appendRow_(LEADERBOARD_SHEET_NAME, LEADERBOARD_COLUMNS, payload);
    }
    return jsonResponse_({ status: 'error', message: 'Missing or unknown "action": ' + action }, 400);
  } catch (err) {
    return jsonResponse_({ status: 'error', message: String(err) }, 500);
  }
}

function appendRow_(sheetName, columns, payload) {
  const missing = columns.filter(c => !(c in payload));
  if (missing.length) {
    return jsonResponse_({ status: 'error', message: 'Missing required fields: ' + missing.join(', ') }, 400);
  }
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(sheetName);
  sheet.appendRow(columns.map(c => payload[c]));
  return jsonResponse_({ status: 'ok', message: 'Row appended to ' + sheetName + '.' }, 200);
}

function doGet(e) {
  // Simple health check -- visiting the deployment URL in a browser should show this.
  return jsonResponse_({ status: 'ok', message: 'Molecular generation leaderboard endpoint is live.' }, 200);
}

function jsonResponse_(obj, code) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
