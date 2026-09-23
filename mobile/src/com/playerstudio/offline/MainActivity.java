package com.playerstudio.offline;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.util.Base64;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;
import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Only packaged assets are served. No Internet or storage permissions required. */
public final class MainActivity extends Activity {
    private static final String HOST = "appassets.androidplatform.net";
    private static final int SAVE_FILE = 10;
    private final ExecutorService io = Executors.newSingleThreadExecutor();
    private WebView web;
    private volatile boolean saving;
    private File pending;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        pending = new File(getCacheDir(), "pending-export.bin");
        saving = state != null && state.getBoolean("saving") && pending.isFile();
        web = new WebView(this);
        web.setBackgroundColor(0xff101217);
        WebSettings settings = web.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        web.setWebChromeClient(new WebChromeClient());
        web.setWebViewClient(new WebViewClient() {
            @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                if (!"https".equals(uri.getScheme()) || !HOST.equals(uri.getHost())) return missing();
                String path = uri.getPath();
                if (path == null || path.contains("..")) return missing();
                if (path.equals("/")) path = "/index.html";
                String mime = path.endsWith(".html") ? "text/html" : path.endsWith(".js") ? "text/javascript" :
                    path.endsWith(".css") ? "text/css" : path.endsWith(".png") ? "image/png" : "application/octet-stream";
                try { return new WebResourceResponse(mime, "UTF-8", getAssets().open(path.substring(1))); }
                catch (Exception error) { return missing(); }
            }
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return true; // A single packaged screen; no external navigation reaches the bridge.
            }
        });
        web.addJavascriptInterface(new FileBridge(), "AndroidFiles");
        setContentView(web);
        // Android 15 enforces edge-to-edge: leave room for status/navigation bars and keyboard.
        web.setOnApplyWindowInsetsListener((view, insets) -> {
            view.setPadding(insets.getSystemWindowInsetLeft(), insets.getSystemWindowInsetTop(),
                insets.getSystemWindowInsetRight(), insets.getSystemWindowInsetBottom());
            return insets.consumeSystemWindowInsets();
        });
        web.loadUrl("https://" + HOST + "/index.html");
    }

    private WebResourceResponse missing() {
        return new WebResourceResponse("text/plain", "UTF-8", 404, "Not Found", null,
            new ByteArrayInputStream(new byte[0]));
    }
    private void message(String text) { runOnUiThread(() -> Toast.makeText(this, text, Toast.LENGTH_LONG).show()); }

    public final class FileBridge {
        @JavascriptInterface public synchronized void save(String name, String mime, String base64) {
            if (saving) { message("请先完成或取消上一次保存"); return; }
            if (name == null || !name.matches("player_[a-z_]+_[a-z0-9]+\\.(png|gif)") ||
                !("image/png".equals(mime) || "image/gif".equals(mime)) || base64 == null || base64.length() > 12000000) {
                message("无效的导出文件"); return;
            }
            saving = true;
            io.execute(() -> {
                try {
                    byte[] bytes = Base64.decode(base64, Base64.DEFAULT);
                    try (OutputStream output = new FileOutputStream(pending)) { output.write(bytes); }
                    runOnUiThread(() -> {
                        try {
                            Intent intent = new Intent(Intent.ACTION_CREATE_DOCUMENT);
                            intent.addCategory(Intent.CATEGORY_OPENABLE);
                            intent.setType(mime);
                            intent.putExtra(Intent.EXTRA_TITLE, name);
                            startActivityForResult(intent, SAVE_FILE);
                        } catch (Exception error) { saving = false; pending.delete(); message("无法打开文件保存窗口"); }
                    });
                } catch (Exception error) { saving = false; pending.delete(); message("生成文件失败，请重试"); }
            });
        }
    }

    @Override protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (request != SAVE_FILE) return;
        if (result != RESULT_OK || data == null || data.getData() == null) {
            saving = false; pending.delete(); message("已取消保存"); return;
        }
        Uri destination = data.getData();
        io.execute(() -> {
            try (InputStream input = new FileInputStream(pending);
                 OutputStream output = getContentResolver().openOutputStream(destination, "wt")) {
                if (output == null) throw new java.io.IOException("No output stream");
                byte[] buffer = new byte[32768]; int length;
                while ((length = input.read(buffer)) != -1) output.write(buffer, 0, length);
                output.flush();
                message("文件已保存");
            } catch (Exception error) { message("保存失败，请重新导出并选择其他位置"); }
            finally { pending.delete(); saving = false; }
        });
    }
    @Override protected void onSaveInstanceState(Bundle state) {
        state.putBoolean("saving", saving); super.onSaveInstanceState(state);
    }
    @Override protected void onPause() {
        web.evaluateJavascript("if(typeof stop==='function')stop();", null);
        web.onPause(); super.onPause();
    }
    @Override protected void onResume() { super.onResume(); if (web != null) web.onResume(); }
    @Override protected void onDestroy() {
        web.removeJavascriptInterface("AndroidFiles"); web.destroy(); io.shutdown(); super.onDestroy();
    }
}
