/**
 * DFT Active Learning tutorial -- leaderboard Web App endpoint.
 *
 * Same pattern as tutorials/12-reaction-bo/leaderboard/apps_script.gs: students POST a JSON payload
 * matching results_schema.csv and this appends one row to the "Leaderboard" tab.
 *
 * IMPORTANT DIFFERENCE FROM THE OTHER TUTORIALS. This board is NOT the final ranking. Students
 * self-report their score on the PUBLIC dev set, because the real test set is hidden from them and
 * they cannot compute their own score on it. After the session the instructor runs
 * `score_submissions.py` over the uploaded checkpoints and publishes the authoritative ranking on
 * the scaffold-disjoint hidden test set.
 *
 * Keeping both boards is deliberate: the movement between them is the tutorial's closing lesson
 * about generalisation. Do not let students believe the live board is the result.
 *
 * ONE-TIME SETUP (see SETUP.md)
 * 1. Google Sheet with one tab named "Leaderboard", header row = results_schema.csv columns.
 * 2. Extensions -> Apps Script, paste this file in.
 * 3. Deploy -> New deployment -> type "Web app" -> execute as "Me" -> who has access "Anyone".
 * 4. Copy the deployment URL into the notebook's LEADERBOARD_ENDPOINT_URL constant.
 */

const SHEET_NAME = 'Leaderboard';

const COLUMNS = [
  'run_id', 'timestamp_utc', 'team_name', 'head', 'ensemble_size', 'seed_method',
  'acquisition', 'n_seed', 'n_rounds', 'batch_size', 'labels_used',
  'dev_smae', 'dev_ence', 'dev_combined', 'dev_aulc', 'dev_spearman',
  'cpu_hours_bought', 'notebook_version', 'notes',
];

// The tutorial's hard budget. A self-reported run above this is flagged rather than rejected --
// the instructor's scorer is what actually disqualifies, from the oracle log.
const BUDGET = 600;

function doPost(e) {
  try {
    const payload = JSON.parse(e.postData.contents);

    const missing = COLUMNS.filter(c => !(c in payload));
    if (missing.length) {
      return jsonResponse_({ status: 'error', message: 'Missing required fields: ' + missing.join(', ') });
    }

    const used = Number(payload.labels_used);
    if (isFinite(used) && used > BUDGET) {
      payload.notes = '[OVER BUDGET: ' + used + '] ' + (payload.notes || '');
    }

    const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
    sheet.appendRow(COLUMNS.map(c => payload[c]));

    return jsonResponse_({ status: 'ok', message: 'Row appended.' });
  } catch (err) {
    return jsonResponse_({ status: 'error', message: String(err) });
  }
}

function doGet(e) {
  // Health check -- visiting the deployment URL in a browser should show this.
  return jsonResponse_({ status: 'ok', message: 'DFT active learning leaderboard endpoint is live.' });
}

function jsonResponse_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
