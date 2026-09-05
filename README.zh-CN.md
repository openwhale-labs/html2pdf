# html2pdf

把 HTML 转成一页连续的 PDF。([English](README.md))

```
html2pdf report.html
```

生成的 PDF 只有一页,宽度由你指定,高度正好等于内容高度,读起来就像在浏览器里滚动这个页面。没有按纸张切的分页,没有每页底部的留白,没有被切成两半的卡片或表格。默认输出是矢量:文字可以选中和搜索,链接可以点,字体内嵌。

## 为什么不用「另存为 PDF」

浏览器的打印对话框一定会把文档切成一张张纸。对于按网页而不是按纸张排的内容,你只能在留白和截断之间选一个。那些先把页面画成 canvas 的前端库输出的是图片,文字就没了。

html2pdf 通过 [Playwright](https://playwright.dev) 驱动无头 Chromium,用 CSS 的 `@page` 规则把页面尺寸声明成渲染后的内容尺寸,并开启 `prefer_css_page_size`。超高的页面这样能正确渲染;实测中把尺寸通过 PDF 接口的宽高参数传入则不能。

## 安装

```
uv tool install git+https://github.com/openwhale-labs/html2pdf
html2pdf --install-browser
```

用 `pipx install git+https://github.com/openwhale-labs/html2pdf` 也一样。第二条命令下载与已安装 Playwright 版本匹配的无头 Chromium。升级 html2pdf 之后如果提示缺少 Chromium,再跑一次。

## 用法

```
html2pdf input.html [output.pdf]

html2pdf input.html --width 1200          # 页面宽度,CSS 像素(默认 1000)
html2pdf input.html --hide ".lang-switch" # 渲染前隐藏指定元素
html2pdf input.html --image               # 整页截图版,用于有 blur、backdrop-filter
                                          # 或柔和渐变的页面
html2pdf input.html --image --scale 3     # 更清晰的截图(默认 2 倍)
html2pdf input.html --paged               # 多页输出,按文档自己的 @page 尺寸
                                          # 和分页规则切页
html2pdf input.html --open                # 生成后打开
```

输出路径默认是输入文件名换成 `.pdf` 后缀。class 为 `toolbar` 的元素会自动隐藏,这是固定在屏幕上的操作条的常见写法,文档里不需要它。`--open` 用系统默认的 PDF 查看器打开。

渲染使用屏幕样式而不是打印样式,并且会等 web 字体加载完成。文档需要自包含:内联 CSS、本地图片或 data URI。要导出一个在运行时切换语言或主题的页面的某个变体,先另存一份把初始状态写死在标记里的 HTML,再转那一份。

`--paged` 用于本身按页设计的文档,比如带 `@page { size: 1280px 720px }` 规则和显式分页符的幻灯片。它按打印媒体渲染,让 Chromium 自行分页。排版视口宽 1280 px(`--width` 更大时取 `--width`)、高 1400 px,所以幻灯片尺寸用 px 而不是 `vw`、`vh`。[`samples/slides.html`](samples/slides.html) 是一个三页的例子。

### 作为库调用

```python
from html2pdf.cli import html_to_pdf

width, height = html_to_pdf("report.html", "report.pdf", width=1000)
```

## 开发

```
git clone https://github.com/openwhale-labs/html2pdf
cd html2pdf
uv tool install -e .
uv run --with pytest pytest
```

没有安装 Playwright 的 Chromium 时(`html2pdf --install-browser`),渲染测试自动跳过。[`samples/sample.html`](samples/sample.html) 比任何一张纸都高,覆盖了固定工具条、表格、卡片和一个超高区块;[`samples/slides.html`](samples/slides.html) 对应 `--paged`。

## 许可证

MIT。Copyright (c) 2026 OpenWhale Labs。
