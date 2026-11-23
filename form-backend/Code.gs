/**
 * 青年百億申請幫手：登記表單的後端。
 *
 * 這是一支綁定在 Google 試算表上的 Apps Script。它接收 docs/index.html 送來的資料，
 * 把文字欄位寫進試算表的一列，把上傳的申請書存到 Google 雲端硬碟的資料夾，並在該列留下檔案連結。
 * 設定步驟見同資料夾的 README.md。
 */

const SHEET_NAME = "登記";
const FOLDER_NAME = "青年百億申請幫手_上傳的申請書";
const MAX_FILE_BYTES = 10 * 1024 * 1024;
const ALLOWED_EXT = ["pdf", "docx"];

// 欄位順序＝試算表的欄位順序。前端送來的其他欄位一律忽略。
const COLUMNS = [
  ["submitted_at", "送出時間"], ["name", "姓名"], ["phone", "手機"], ["email", "Email"], ["birth_year", "出生年"],
  ["status", "目前身分"], ["education", "學歷"], ["experience", "經歷"], ["skills", "專長與技能"],
  ["interests", "興趣與關注的議題"], ["languages", "語言能力"], ["target", "想申請的計畫"], ["gap", "還缺什麼"],
  ["guardian_consent", "法定代理人同意"], ["file_url", "申請書檔案"],
];
const LIMITS = { name: 40, phone: 20, email: 120, birth_year: 4, status: 80, education: 2000, experience: 6000,
  skills: 1500, interests: 1500, languages: 200, target: 200, gap: 2000, guardian_consent: 10 };

function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    if (data.website) return reply({ ok: true });            // 隱藏欄位被填了，視為機器人：假裝成功但不寫入

    for (const key of ["name", "phone", "email", "birth_year", "status", "education", "experience"]) {
      if (!String(data[key] || "").trim()) return reply({ ok: false, error: "缺少必填欄位" });
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.email)) return reply({ ok: false, error: "Email 格式不正確" });

    const row = {};
    Object.keys(LIMITS).forEach(function (key) { row[key] = safeCell(String(data[key] || "").slice(0, LIMITS[key])); });
    row.submitted_at = Utilities.formatDate(new Date(), "Asia/Taipei", "yyyy-MM-dd HH:mm:ss");
    row.file_url = data.file_base64 ? saveFile(data, row.name) : "";

    const lock = LockService.getScriptLock();              // 避免兩筆同時寫入時互相覆蓋
    lock.waitLock(20000);
    try {
      getSheet().appendRow(COLUMNS.map(function (c) { return row[c[0]] || ""; }));
    } finally {
      lock.releaseLock();
    }
    return reply({ ok: true });
  } catch (err) {
    console.error(err);
    return reply({ ok: false, error: "伺服器處理失敗" });
  }
}

function doGet() {
  return reply({ ok: true, message: "登記表單後端運作中" });
}

/** 以「=、+、-、@」開頭的內容前面加上單引號，避免在試算表中被當成公式執行。 */
function safeCell(text) {
  return /^[=+\-@]/.test(text) ? "'" + text : text;
}

function saveFile(data, name) {
  const fileName = String(data.file_name || "draft");
  const ext = fileName.split(".").pop().toLowerCase();
  if (ALLOWED_EXT.indexOf(ext) === -1) throw new Error("不接受的檔案類型");
  const bytes = Utilities.base64Decode(data.file_base64);
  if (bytes.length > MAX_FILE_BYTES) throw new Error("檔案太大");
  const stamp = Utilities.formatDate(new Date(), "Asia/Taipei", "yyyyMMdd_HHmmss");
  const clean = String(name).replace(/[\\/:*?"<>|]/g, "_").slice(0, 30);
  const mime = ext === "pdf" ? "application/pdf" : "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
  const file = getFolder().createFile(Utilities.newBlob(bytes, mime, stamp + "_" + clean + "." + ext));
  return file.getUrl();                                     // 檔案維持私人，只有試算表擁有者能開啟
}

function getSheet() {
  const book = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = book.getSheetByName(SHEET_NAME);
  if (!sheet) {
    sheet = book.insertSheet(SHEET_NAME);
    sheet.appendRow(COLUMNS.map(function (c) { return c[1]; }));
    sheet.setFrozenRows(1);
  }
  return sheet;
}

function getFolder() {
  const props = PropertiesService.getScriptProperties();
  const id = props.getProperty("FOLDER_ID");
  if (id) {
    try { return DriveApp.getFolderById(id); } catch (err) { /* 資料夾被刪掉了，重新建立 */ }
  }
  const folder = DriveApp.createFolder(FOLDER_NAME);
  props.setProperty("FOLDER_ID", folder.getId());
  return folder;
}

function reply(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

/** 第一次設定時在編輯器裡手動執行一次，用來授權並建立工作表與資料夾。 */
function setup() {
  getSheet();
  getFolder();
}
