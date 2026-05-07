# Giám sát đường mạng — ĐH Ngoại thương

Hệ thống tự động theo dõi 26 đường mạng tại 3 cơ sở (Hà Nội, TP HCM, Quảng Ninh).
Toàn bộ hạ tầng chạy miễn phí trên GitHub.

```
GitHub Actions (cron 5 phút)
       │  ping toàn bộ IP từ server GitHub
       ▼
 status.json trong repo
       │
   ┌───┴────────────────────┐
   ▼                        ▼
 Web dashboard           App Android
 (GitHub Pages)          (APK auto-build)
                              │
                              ▼
                       Thông báo native khi
                       có đường mạng mất
```

## Anh chỉ cần làm 4 việc (~10 phút):

### Bước 1 — Tạo repo trống trên GitHub

1. Mở **https://github.com/new** (đăng nhập GitHub nếu chưa)
2. Trong **Repository name**: gõ `network-monitor` (hoặc tên khác tùy anh, không dấu)
3. **Public** hoặc **Private** đều được (Public thì GitHub Pages free; Private cần GitHub Pro)
4. **KHÔNG** tick "Add a README", "Add .gitignore", "Choose a license" — để repo trống hoàn toàn
5. Bấm nút xanh **Create repository**

### Bước 2 — Đẩy code lên (1 lệnh)

Mở **PowerShell** trong thư mục project rồi chạy:

```powershell
.\push-to-github.ps1 -GithubUser "TEN-GITHUB-CUA-ANH" -RepoName "network-monitor"
```

Thay `TEN-GITHUB-CUA-ANH` bằng username GitHub của anh, và `network-monitor` bằng đúng tên repo vừa tạo ở Bước 1.

Lần đầu sẽ hỏi đăng nhập GitHub — login bằng tài khoản của anh.

### Bước 3 — Bật GitHub Pages

1. Vào **Settings → Pages** của repo (link script đã in ra)
2. Trong **Build and deployment → Source**, chọn **GitHub Actions**
3. Đợi ~1 phút, GitHub tự deploy trang web

### Bước 4 — Kích hoạt monitor lần đầu + chờ APK build

1. Vào **Actions → Monitor network lines → Run workflow** (link script đã in)
2. Vào **Actions → Build Android APK**, chờ build xong (~3–5 phút lần đầu)
3. Vào **Releases → latest**, tải file `.apk` về điện thoại Android, cài đặt

---

## Sau khi xong, anh có:

- **Trang web dashboard** ở `https://TEN-GITHUB.github.io/network-monitor/` — mở trên máy tính, tự refresh mỗi 30 giây.
- **App Android** trên điện thoại — bật ra xem trạng thái, tự kiểm tra ngầm mỗi 15 phút và **bắn thông báo** khi có đường mạng nào mất hoặc hoạt động lại.

---

## Cấu trúc thư mục

```
.
├── monitor/
│   ├── ips.json              # Danh sách 26 IP (sửa ở đây nếu thêm/bớt đường)
│   ├── check.py              # Script ping, gọi từ GitHub Actions
│   ├── make_icons.py         # Sinh icon cho web PWA
│   └── make_android_icons.py # Sinh icon launcher cho app Android
│
├── web/                      # Dashboard tĩnh
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   ├── sw.js                 # Service worker (offline shell)
│   ├── manifest.webmanifest
│   └── icons/
│
├── android-src/              # App Android (Kotlin native, không Capacitor)
│   ├── app/
│   │   ├── build.gradle.kts
│   │   └── src/main/
│   │       ├── AndroidManifest.xml
│   │       ├── java/vn/edu/ftu/netmon/
│   │       │   ├── MainActivity.kt
│   │       │   ├── MonitorApplication.kt
│   │       │   ├── MonitorWorker.kt   # background polling + thông báo
│   │       │   └── BootReceiver.kt
│   │       └── res/...
│   ├── build.gradle.kts
│   ├── gradle.properties
│   └── settings.gradle.kts
│
├── data/                     # Trạng thái + lịch sử (do CI tự ghi)
│   ├── status.json
│   └── history.json
│
├── .github/workflows/
│   ├── monitor.yml           # Cron 5 phút: ping IP, commit status
│   ├── deploy-pages.yml      # Deploy web lên GitHub Pages
│   └── build-apk.yml         # Build APK + tạo Release
│
├── push-to-github.ps1        # Script đẩy lên GitHub (anh chạy 1 lần)
└── README.md
```

## Khi nào cần sửa gì?

| Thay đổi | Sửa file | Sau đó |
|---|---|---|
| Thêm/bớt đường mạng | `monitor/ips.json` | Commit + push, monitor tự áp dụng lần ping kế tiếp |
| Đổi giao diện web | `web/style.css`, `web/app.js`, `web/index.html` | Push, GitHub Pages tự deploy lại |
| Đổi tên app Android, icon | `android-src/app/src/main/res/values/strings.xml`, đổi PNG trong `mipmap-*/` | Push, APK tự build lại trong vài phút |
| Đổi chu kỳ ping (5 phút → khác) | `.github/workflows/monitor.yml`, dòng `cron: "*/5 * * * *"` | Push, lần chạy kế tiếp dùng cấu hình mới |

## Câu hỏi thường gặp

**Có tốn tiền gì không?**
Không. GitHub Actions cho phép 2000 phút/tháng miễn phí với repo public. Job ping của mình ~30 giây, chạy 12 lần/giờ = ~6 phút/ngày = ~180 phút/tháng. GitHub Pages free, build APK free, không có chi phí ẩn.

**App Android có hoạt động khi tắt màn hình không?**
Có. WorkManager chạy nền, kiểm tra mỗi 15 phút (giới hạn của Android, không thể nhỏ hơn). Khi phát hiện đường mạng mất, thông báo bật lên ngay, kèm âm thanh + rung.

**Nếu tôi muốn check mỗi phút thay vì mỗi 5 phút?**
GitHub Actions cron tối thiểu 5 phút. Nếu muốn nhanh hơn cần host backend riêng (VPS), nhưng 5 phút thường đủ cho mạng campus.

**Một vài IP báo "MẤT" dù vẫn dùng được — sao vậy?**
Một số nhà mạng chặn ICMP (chặn ping) ở IP gateway. Script đã có fallback TCP cổng 80/443/53. Nếu vẫn không thông được, anh có thể:
- Sửa danh sách `tcp_fallback_ports` trong `ips.json` (vd thêm cổng 22, 8080)
- Hoặc đổi sang IP khác trong cùng dải mà anh biết phản hồi
