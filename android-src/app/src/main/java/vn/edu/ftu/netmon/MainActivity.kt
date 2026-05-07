package vn.edu.ftu.netmon

import android.Manifest
import android.annotation.SuppressLint
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.view.View
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import vn.edu.ftu.netmon.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {
    private lateinit var b: ActivityMainBinding

    private val notificationPermLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { /* No-op: monitoring still works, user just won't get banner */ }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        b = ActivityMainBinding.inflate(layoutInflater)
        setContentView(b.root)

        requestNotificationPermissionIfNeeded()

        with(b.webview.settings) {
            javaScriptEnabled = true
            domStorageEnabled = true
            cacheMode = WebSettings.LOAD_DEFAULT
            mediaPlaybackRequiresUserGesture = false
            setSupportZoom(false)
        }
        b.webview.webChromeClient = WebChromeClient()
        b.webview.webViewClient = object : WebViewClient() {
            override fun onPageFinished(view: WebView?, url: String?) {
                b.swipeRefresh.isRefreshing = false
                b.errorView.visibility = View.GONE
            }
            override fun onReceivedError(
                view: WebView?,
                request: WebResourceRequest?,
                error: WebResourceError?
            ) {
                if (request?.isForMainFrame == true) {
                    b.swipeRefresh.isRefreshing = false
                    b.errorView.visibility = View.VISIBLE
                }
            }
        }

        b.swipeRefresh.setOnRefreshListener {
            b.errorView.visibility = View.GONE
            b.webview.reload()
        }
        b.retryButton.setOnClickListener {
            b.errorView.visibility = View.GONE
            b.webview.loadUrl(BuildConfig.DASHBOARD_URL)
        }

        if (savedInstanceState == null) {
            b.webview.loadUrl(BuildConfig.DASHBOARD_URL)
        }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        b.webview.saveState(outState)
        super.onSaveInstanceState(outState)
    }

    override fun onRestoreInstanceState(savedInstanceState: Bundle) {
        super.onRestoreInstanceState(savedInstanceState)
        b.webview.restoreState(savedInstanceState)
    }

    @Deprecated("Deprecated in API 33+, but we still support old Android")
    override fun onBackPressed() {
        if (b.webview.canGoBack()) {
            b.webview.goBack()
        } else {
            @Suppress("DEPRECATION")
            super.onBackPressed()
        }
    }

    private fun requestNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return
        val granted = ContextCompat.checkSelfPermission(
            this, Manifest.permission.POST_NOTIFICATIONS
        ) == PackageManager.PERMISSION_GRANTED
        if (!granted) {
            notificationPermLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
    }
}
