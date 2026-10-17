(() => {
  "use strict";

  const copy = Object.freeze({
    vi: Object.freeze({
      title: "Bạn đang ngoại tuyến",
      message: "Trang công khai này hiện không thể tải từ mạng. Hãy kết nối lại Internet rồi thử. Thông tin tài khoản và không gian riêng tư không được lưu vào bộ nhớ ngoại tuyến.",
      retry: "Thử lại",
      language: "Chọn ngôn ngữ",
    }),
    en: Object.freeze({
      title: "You’re offline",
      message: "This public page is not available over the network. Reconnect to the internet and try again. Account information and private workspace data are not stored offline.",
      retry: "Try again",
      language: "Choose language",
    }),
    zh: Object.freeze({
      title: "当前处于离线状态",
      message: "此公共页面目前无法通过网络加载。请重新连接网络后重试。账户信息和私人工作区数据不会保存在离线缓存中。",
      retry: "重试",
      language: "选择语言",
    }),
  });

  const languageSwitch = document.querySelector("[data-offline-language-switcher]");
  const title = document.querySelector("[data-offline-title]");
  const message = document.querySelector("[data-offline-message]");
  const retry = document.querySelector("[data-offline-retry]");
  if (!languageSwitch || !title || !message || !retry) return;

  const buttons = Array.from(languageSwitch.querySelectorAll("[data-offline-locale]"));
  function setLocale(value) {
    const locale = Object.prototype.hasOwnProperty.call(copy, value) ? value : "vi";
    const strings = copy[locale];
    document.documentElement.lang = locale;
    document.title = `TOAN AAS — ${strings.title}`;
    title.textContent = strings.title;
    message.textContent = strings.message;
    retry.textContent = strings.retry;
    languageSwitch.setAttribute("aria-label", strings.language);
    buttons.forEach((button) => {
      button.setAttribute("aria-pressed", button.dataset.offlineLocale === locale ? "true" : "false");
    });
  }

  buttons.forEach((button) => {
    button.addEventListener("click", () => setLocale(button.dataset.offlineLocale));
  });

  const browserLocale = String(window.navigator && window.navigator.language || "vi")
    .split(/[-_]/, 1)[0]
    .toLowerCase();
  setLocale(Object.prototype.hasOwnProperty.call(copy, browserLocale) ? browserLocale : "vi");
})();
