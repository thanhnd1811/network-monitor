# Hướng dẫn cài Local Probe lên máy ở trường

Mục đích: chạy 1 chương trình nhỏ trên máy ở trường (đang nối mạng VN), ping toàn bộ 26 đường mạng từ trong nước rồi đẩy kết quả lên GitHub. Kết quả chính xác hơn nhiều so với để GitHub Actions ping từ Mỹ.

**Tổng thời gian setup: ~10 phút.**

---

## Bước 1 — Tạo Personal Access Token GitHub (PAT)

PAT giống như mật khẩu nhưng giới hạn quyền — máy ở trường dùng nó để ghi file `data/status.json` lên repo, không truy cập được gì khác.

1. Mở: **https://github.com/settings/personal-access-tokens/new**
2. Điền:
   - **Token name**: `ftu-netmon-probe` (hoặc tên anh thích)
   - **Resource owner**: `thanhnd1811`
   - **Expiration**: 1 year (hoặc "No expiration")
   - **Repository access**: chọn **"Only select repositories"** → chọn repo `network-monitor`
3. Mục **Repository permissions** → tìm **"Contents"** → đổi từ "No access" sang **"Read and write"**
4. Cuộn xuống cuối → bấm **"Generate token"**
5. **Copy ngay lập tức** chuỗi token bắt đầu bằng `github_pat_...` — sau khi đóng trang sẽ KHÔNG xem lại được.

> Lưu chuỗi này tạm vào Notepad. Bước 3 sẽ dán vào.

---

## Bước 2 — Copy folder sang máy ở trường

Toàn bộ thư mục **`local-monitor`** chỉ chứa 4 file cần copy:

```
local-monitor/
├── ftu-netmon-probe.exe       ← chương trình chính (9MB, không cần Python)
├── config.json.example        ← mẫu cấu hình
├── install-task.ps1           ← script cài Scheduled Task
└── HƯỚNG DẪN CÀI.md           ← file này
```

Cách copy: nén `local-monitor` thành file zip → gửi qua USB/email/Drive sang máy ở trường → giải nén ra thư mục bất kỳ, ví dụ `C:\NetMon\`.

---

## Bước 3 — Tạo file config.json (trên máy ở trường)

1. Trong thư mục `C:\NetMon\` (chỗ anh giải nén), copy file **`config.json.example`** thành **`config.json`**
2. Mở `config.json` bằng Notepad
3. Tìm dòng:
   ```json
   "github_token": "PASTE-PERSONAL-ACCESS-TOKEN-HERE",
   ```
4. Thay chuỗi `PASTE-PERSONAL-ACCESS-TOKEN-HERE` bằng token vừa copy ở Bước 1 (vẫn để trong dấu nháy kép). Ví dụ:
   ```json
   "github_token": "github_pat_11AABBCCDD_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
   ```
5. Save lại (Ctrl+S).

> **Không cần sửa gì khác** trong config.json. Phần `locations` đã có đầy đủ 26 IP.

---

## Bước 4 — Cài Scheduled Task (chạy tự động mỗi 1 phút)

1. **Click chuột phải** vào file `install-task.ps1`
2. Chọn **"Run with PowerShell"** (nếu chỉ thấy "Open" thì right-click → "Run as administrator")
3. Nếu Windows hỏi "Allow this app to make changes" → Yes
4. Script sẽ:
   - Test chạy probe 1 lần (xem có ping được không, có push được lên GitHub không)
   - Nếu OK, tạo Scheduled Task chạy mỗi 1 phút (kể cả khi máy không có ai login)
   - Khởi động task ngay lập tức

Nếu thấy dòng cuối **"XONG!"** màu xanh → đã thành công.

---

## Bước 5 — Kiểm tra

1. Mở web dashboard: https://thanhnd1811.github.io/network-monitor/
2. Sau ~1-2 phút, chỗ "Cập nhật" sẽ hiện thời gian rất gần (vài chục giây)
3. Số đường UP sẽ tăng lên đáng kể (hy vọng ~20-25/26)

Xem log chi tiết trong file `probe.log` (cùng thư mục với probe.exe).

---

## Khi cần bảo trì

| Việc | Cách làm |
|---|---|
| Đổi token (token hết hạn) | Mở config.json, dán token mới, save. Task tự dùng config mới ở lần chạy kế tiếp. |
| Xem log | Mở `probe.log` |
| Tạm dừng task | Mở Task Scheduler (Win+R → `taskschd.msc`) → tìm "FTU NetMon Probe" → click phải → Disable |
| Chạy ngay không đợi | Trong Task Scheduler, click phải task → "Run" |
| Gỡ bỏ hẳn | PowerShell admin: `Unregister-ScheduledTask -TaskName "FTU NetMon Probe" -Confirm` |
| Đổi tần suất (vd 30 giây) | Chạy lại install-task.ps1 với tham số `-IntervalMinutes 0` (không khả thi, min 1 phút). Hoặc edit task trong taskschd.msc. |
| Thêm/bớt IP | Sửa `monitor/ips.json` trong repo, commit lên GitHub. Trên máy ở trường: cũng phải sửa `config.json` cho khớp (hoặc tải lại config.json.example mới). |

## Bảo mật

- **PAT chỉ có quyền Contents:Read/Write trên 1 repo này** — kể cả lộ token, chỉ ảnh hưởng repo `network-monitor`, không ảnh hưởng tài khoản hay repo khác.
- Để cẩn thận hơn, anh có thể đặt expiration token 90 ngày, lập lịch nhắc đổi.
- File `probe.log` có thể chứa IP public của trường — không nên gửi cho người ngoài.
