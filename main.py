import threading
import base64
import requests
import json
import imghdr
import os

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle
from kivy.core.text import LabelBase

key=os.environ.get("BAIDU_API_KEY", "")

# 尝试导入Plyer
try:
    from plyer import camera, filechooser
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False

# ================== 字体设置 ==================
FONT_PATH = 'msyh.ttc'
try:
    LabelBase.register(name='ChineseFont', fn_regular=FONT_PATH)
    FONT_NAME = 'ChineseFont'
except:
    FONT_NAME = 'Roboto'
    print("未找到中文字体，将使用默认字体（中文可能显示为方块）")

# ================== 百度API配置 ==================

def image_to_base64(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')


def get_image_format(image_path):
    try:
        format_type = imghdr.what(image_path)
        if format_type:
            return format_type
    except Exception as e:
        print(f"imghdr识别失败: {e}")
        return None

def analyze_image_with_baidu(image_path):
    gs=get_image_format(image_path)
    print(gs)
    base64=image_to_base64(image_path)
    url = "https://qianfan.baidubce.com/v2/chat/completions"
    payload = json.dumps({
        "model": "ernie-5.0",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "图片中是否有口腔问题"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "data:image/"+gs+";base64,"+base64
                        }
                    }
                ]
            }
        ]
    })
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer '+key
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    return json.loads(response.text)['choices'][0]['message']['content']

def analyze_text_with_baidu(text):
    print(text)
    url = "https://qianfan.baidubce.com/v2/chat/completions"
    payload = json.dumps({
        "model": "deepseek-v4-pro-0813",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "你是一位口腔专家，你只回答口腔相关的问题，其它问题请回答：这不在我的处理范围内，请咨询口腔问题，如果是向你问好，那也可以礼貌回应"
                    },
                    {
                        "type": "text",
                        "text": text
                    }
                ]
            },
        ],
        "web_search": {
            "enable": False,
            "enable_citation": False,
            "enable_trace": False
        },
        "plugin_options": {}
    }, ensure_ascii=False)
    headers = {
        'Content-Type': 'application/json',
        'appid': '',
        'Authorization': 'Bearer ' + key
    }

    response = requests.request("POST", url, headers=headers, data=payload.encode("utf-8"))
    print(response.text)
    return json.loads(response.text)['choices'][0]['message']['content']

# ================== 自定义圆角输入框 ==================
class RoundedTextInput(TextInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_active = ''
        self.border = (0, 0, 0, 0)
        self.padding = [15, 10]
        self.font_name = FONT_NAME
        self.font_size = 16
        self.foreground_color = (0, 0, 0, 1)  # 纯黑文字
        self.cursor_color = (0.25, 0.55, 0.95, 1)
        self.hint_text_color = (0.5, 0.5, 0.5, 1)

        # 使用 background_color 设置浅灰背景，确保文字可见
        self.background_color = (0.95, 0.95, 0.95, 1)
        # 圆角可以通过 border 和 background_normal 的九宫格实现，但为简单，
        # 这里不绘制复杂背景，保持默认矩形（可接受）
        # 如果需要圆角，可参考：https://kivy.org/doc/stable/api-kivy.uix.textinput.html

# ================== 圆角按钮（继承 Button） ==================
class RoundedButton(Button):
    def __init__(self, text="", **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.size_hint = (None, None)
        self.size = (50, 50)
        self.font_name = FONT_NAME
        self.font_size = 24
        self.color = (1, 1, 1, 1)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0)  # 透明，由canvas绘制背景
        self.border = (0, 0, 0, 0)

        # 绘制蓝色圆形背景
        with self.canvas.before:
            self.bg_color = Color(0.25, 0.55, 0.95, 1)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[25])
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

# ================== 消息气泡 ==================
class MessageBubble(Label):
    def __init__(self, text, is_user=False, **kwargs):
        super().__init__(**kwargs)
        self.is_user = is_user
        self.text = text
        self.font_name = FONT_NAME
        self.font_size = 16
        self.padding_x = 10
        self.padding_y = 8
        self.size_hint = (None, None)
        self.max_width = Window.width * 0.7
        self.text_size = (self.max_width, None)
        self.halign = 'right' if is_user else 'left'
        self.valign = 'middle'
        self.color = (1, 1, 1, 1) if is_user else (0.1, 0.1, 0.1, 1)
        self.bind(texture_size=self._update_size)

        with self.canvas.before:
            if is_user:
                Color(0.25, 0.55, 0.95, 1)
            else:
                Color(0.95, 0.95, 0.95, 1)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[10])
        self.bind(pos=self._update_rect, size=self._update_rect)
        Clock.schedule_once(lambda dt: self._update_size(), 0)

    def _update_size(self, *args):
        width = min(self.texture_size[0] + self.padding_x * 2, self.max_width)
        height = self.texture_size[1] + self.padding_y * 2
        self.size = (width, height)
        self.text_size = (width - self.padding_x * 2, None)

    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

# ================== 主应用 ==================
class OralHealthApp(App):
    def build(self):
        self.title = "AI口腔诊断助手"
        Window.clearcolor = (1, 1, 1, 1)

        root = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # 标题
        title_label = Label(
            text="AI口腔诊断助手",
            size_hint_y=None,
            height=40,
            font_size=20,
            font_name=FONT_NAME,
            color=(0.1, 0.1, 0.1, 1),
            bold=True
        )
        root.add_widget(title_label)

        # 消息滚动区域
        self.scroll = ScrollView(size_hint=(1, 0.85))
        self.message_box = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=8,
            padding=[0, 5, 0, 5]
        )
        self.message_box.bind(minimum_height=self.message_box.setter('height'))
        self.scroll.add_widget(self.message_box)
        root.add_widget(self.scroll)

        # 底部输入栏
        input_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=60, spacing=10)

        # 圆角输入框（使用标准背景色，确保文字可见）
        self.text_input = RoundedTextInput(
            hint_text="请输入症状描述...",
            multiline=False,
            size_hint=(1, 1)
        )
        self.text_input.bind(on_text_validate=self.send_message)
        input_bar.add_widget(self.text_input)

        # 按钮容器
        btn_container = BoxLayout(orientation='horizontal', size_hint_x=None, width=110, spacing=8)

        # 拍照按钮（圆角，使用 + 符号）
        self.img_button = RoundedButton(text="+")
        self.img_button.bind(on_release=self.show_image_options)
        btn_container.add_widget(self.img_button)

        # 发送按钮（圆角，使用 > 符号）
        self.send_button = RoundedButton(text=">")
        self.send_button.bind(on_release=self.send_message)
        btn_container.add_widget(self.send_button)

        input_bar.add_widget(btn_container)
        root.add_widget(input_bar)

        # 初始焦点给输入框
        Clock.schedule_once(lambda dt: setattr(self.text_input, 'focus', True), 0.1)
        return root

    # ================== 消息发送与处理 ==================
    def send_message(self, instance=None):
        print("发送按钮被点击")
        text = self.text_input.text.strip()
        if not text:
            print("输入为空，不发送")
            return
        self.add_message(text, is_user=True)
        self.text_input.text = ""
        loading_bubble = self.add_message("AI分析中...", is_user=False, is_loading=True)
        threading.Thread(target=self._process_text, args=(text, loading_bubble)).start()

    def _process_text(self, text, loading_bubble):
        try:
            reply = analyze_text_with_baidu(text)
            print(reply)
        except Exception as e:
            reply = f"处理出错: {e}"
        Clock.schedule_once(lambda dt: self._replace_loading(loading_bubble, reply))

    def show_image_options(self, instance):
        print("拍照按钮被点击")
        if not PLYER_AVAILABLE:
            self.add_message("当前设备不支持图片功能（缺少Plyer库）。", is_user=False)
            return
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        btn_camera = Button(text="拍照", background_normal='', background_color=(0.25,0.55,0.95,1), font_name=FONT_NAME, color=(1,1,1,1))
        btn_gallery = Button(text="从相册选择", background_normal='', background_color=(0.25,0.55,0.95,1), font_name=FONT_NAME, color=(1,1,1,1))
        btn_cancel = Button(text="取消", background_normal='', background_color=(0.7,0.7,0.7,1), font_name=FONT_NAME, color=(1,1,1,1))
        content.add_widget(btn_camera)
        content.add_widget(btn_gallery)
        content.add_widget(btn_cancel)
        popup = Popup(title="选择图片来源", content=content, size_hint=(0.8, 0.35), title_font=FONT_NAME)
        btn_camera.bind(on_release=lambda x: self._take_photo(popup))
        btn_gallery.bind(on_release=lambda x: self._choose_photo(popup))
        btn_cancel.bind(on_release=popup.dismiss)
        popup.open()

    def _take_photo(self, popup):
        popup.dismiss()
        try:
            camera.take_picture(filename='oral_photo.jpg', on_complete=self._process_image)
        except Exception as e:
            self.add_message(f"拍照失败: {e}", is_user=False)

    def _choose_photo(self, popup):
        popup.dismiss()
        try:
            filechooser.open_file(on_selection=self._process_selected_file, filters=["*.jpg", "*.png", "*.jpeg"])
        except Exception as e:
            self.add_message(f"文件选择失败: {e}", is_user=False)

    def _process_selected_file(self, selection):
        if selection and len(selection) > 0:
            self._process_image(selection[0])

    def _process_image(self, image_path):
        self.add_message("[已上传图片]", is_user=True)
        loading_bubble = self.add_message("AI图像分析中...请等待", is_user=False, is_loading=True)
        threading.Thread(target=self._analyze_image, args=(image_path, loading_bubble)).start()

    def _analyze_image(self, image_path, loading_bubble):
        try:
            reply = analyze_image_with_baidu(image_path)
        except Exception as e:
            reply = f"图像分析出错: {e}"
        Clock.schedule_once(lambda dt: self._replace_loading(loading_bubble, reply))

    def add_message(self, text, is_user=False, is_loading=False):
        bubble = MessageBubble(text=text, is_user=is_user)
        self.message_box.add_widget(bubble)
        Clock.schedule_once(lambda dt: setattr(self.scroll, 'scroll_y', 0), 0.1)
        return bubble

    def _replace_loading(self, loading_bubble, reply_text):
        self.message_box.remove_widget(loading_bubble)
        self.add_message(reply_text, is_user=False)

if __name__ == "__main__":
    OralHealthApp().run()
