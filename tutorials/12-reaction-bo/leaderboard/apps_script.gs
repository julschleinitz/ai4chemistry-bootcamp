/**
 * Reaction BO tutorial -- leaderboard Web App endpoint.
 *
 * Mirrors the "Google Sheets handoff" pattern from
 * tutorials/06-pretraining_finetuning/leaderboard/apps_script.gs: students self-compute their run's
 * BO metrics (auc_mean, auc_std, max_score_achieved) inside reaction-bo.ipynb, then POST a JSON
 * payload matching results_schema.csv to this Web App, which appends one row to the "Leaderboard"
 * tab. No secret answer key, no Drive folder, no file parsing -- there is no independent grading
 * oracle for this tutorial, so this is purely a self-report leaderboard.
 *
 * ONE-TIME SETUP (see SETUP.md)
 * 1. Create a Google Sheet with one tab named "Leaderboard", header row = results_schema.csv columns.
 * 2. Extensions -> Apps Script, paste this file in.
 * 3. Deploy -> New deployment -> type "Web app" -> execute as "Me" -> who has access "Anyone".
 * 4. Copy the deployment URL into the notebook's LEADERBOARD_ENDPOINT_URL constant.
 */

const SHEET_NAME = 'Leaderboard';

const COLUMNS = [
  'run_id', 'timestamp_utc', 'team_name', 'dataset', 'featurization', 'init_method',
  'acquisition', 'acquisition_hparams', 'batch_size', 'n_rounds', 'n_seeds',
  'auc_mean', 'auc_std', 'max_score_achieved', 'notebook_version', 'notes',
];

function doPost(e) {
  try {
    const payload = JSON.parse(e.postData.contents);

    const missing = COLUMNS.filter(c => !(c in payload));
    if (missing.length) {
      return jsonResponse_({ status: 'error', message: 'Missing required fields: ' + missing.join(', ') }, 400);
    }

    const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
    sheet.appendRow(COLUMNS.map(c => payload[c]));

    return jsonResponse_({ status: 'ok', message: 'Row appended.' }, 200);
  } catch (err) {
    return jsonResponse_({ status: 'error', message: String(err) }, 500);
  }
}

function doGet(e) {
  // Simple health check -- visiting the deployment URL in a browser should show this.
  return jsonResponse_({ status: 'ok', message: 'Reaction BO leaderboard endpoint is live.' }, 200);
}

function jsonResponse_(obj, code) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
