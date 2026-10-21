// EV3 Simulator — Windows shell.
// Serves the embedded simulator on localhost and opens it in an app-style window
// (Microsoft Edge or Google Chrome in --app mode). Falls back to the default browser.
package main

import (
	_ "embed"
	"fmt"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync/atomic"
	"syscall"
	"time"
	"unsafe"
)

//go:embed index.html
var page []byte

const fixedPort = 47123

var lastPing atomic.Int64

func messageBox(text, title string) {
	u32 := syscall.NewLazyDLL("user32.dll")
	mb := u32.NewProc("MessageBoxW")
	t, _ := syscall.UTF16PtrFromString(text)
	c, _ := syscall.UTF16PtrFromString(title)
	mb.Call(0, uintptr(unsafe.Pointer(t)), uintptr(unsafe.Pointer(c)), 0x40)
}

func findBrowser() string {
	env := func(k string) string { return os.Getenv(k) }
	cands := []string{
		filepath.Join(env("ProgramFiles(x86)"), `Microsoft\Edge\Application\msedge.exe`),
		filepath.Join(env("ProgramFiles"), `Microsoft\Edge\Application\msedge.exe`),
		filepath.Join(env("LocalAppData"), `Microsoft\Edge\Application\msedge.exe`),
		filepath.Join(env("ProgramFiles"), `Google\Chrome\Application\chrome.exe`),
		filepath.Join(env("ProgramFiles(x86)"), `Google\Chrome\Application\chrome.exe`),
		filepath.Join(env("LocalAppData"), `Google\Chrome\Application\chrome.exe`),
	}
	for _, c := range cands {
		if c != "" {
			if st, err := os.Stat(c); err == nil && !st.IsDir() {
				return c
			}
		}
	}
	return ""
}

func main() {
	ln, err := net.Listen("tcp", fmt.Sprintf("127.0.0.1:%d", fixedPort))
	if err != nil {
		ln, err = net.Listen("tcp", "127.0.0.1:0")
		if err != nil {
			messageBox("تعذّر تشغيل المحاكي: "+err.Error(), "محاكي EV3")
			return
		}
	}
	url := fmt.Sprintf("http://%s/", ln.Addr().String())
	// heartbeat so the app closes itself when its window is closed
	beat := []byte(`<script>setInterval(function(){fetch('/__ping').catch(function(){})},4000)</script></body>`)
	html := []byte(strings.Replace(string(page), "</body>", string(beat), 1))

	mux := http.NewServeMux()
	mux.HandleFunc("/__ping", func(w http.ResponseWriter, r *http.Request) {
		lastPing.Store(time.Now().Unix())
		w.WriteHeader(204)
	})
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/" && r.URL.Path != "/index.html" {
			http.NotFound(w, r)
			return
		}
		lastPing.Store(time.Now().Unix())
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		w.Header().Set("Cache-Control", "no-store")
		w.Write(html)
	})
	go http.Serve(ln, mux)

	browser := findBrowser()
	if browser != "" {
		profile := filepath.Join(os.Getenv("LocalAppData"), "EV3Simulator", "browser")
		os.MkdirAll(profile, 0o755)
		cmd := exec.Command(browser, "--app="+url, "--user-data-dir="+profile, "--window-size=1440,900",
			"--no-first-run", "--no-default-browser-check", "--disable-features=Translate", "--lang=ar")
		cmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: true}
		if err := cmd.Start(); err == nil {
			done := make(chan struct{})
			go func() { cmd.Wait(); close(done) }()
			// the browser may hand off to an existing process; rely on the heartbeat too
			lastPing.Store(time.Now().Unix() + 30)
			for {
				select {
				case <-done:
					done = nil
					if time.Now().Unix()-lastPing.Load() > 12 {
						return
					}
				case <-time.After(3 * time.Second):
					if time.Now().Unix()-lastPing.Load() > 15 {
						return
					}
				}
			}
		}
	}
	// fallback: default browser
	exec.Command("rundll32", "url.dll,FileProtocolHandler", url).Start()
	lastPing.Store(time.Now().Unix() + 60)
	for time.Now().Unix()-lastPing.Load() < 20 {
		time.Sleep(3 * time.Second)
	}
}
