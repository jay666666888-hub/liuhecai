#!/usr/bin/env python3
"""
策略搜索系统 API
================

提供HTTP API用于查询策略和执行预测
"""

import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, '/home/admin1/liuhecai_strategy_search')

from features.feature_engine import FeatureBuilder
from strategies.executor import StrategyExecutor

class APIHandler(BaseHTTPRequestHandler):
    """API请求处理器"""

    strategies = None
    df = None
    fb = None
    executor = None

    def do_GET(self):
        """处理GET请求"""
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == '/health':
            self.send_json({'status': 'ok', 'strategies': len(self.strategies)})

        elif path == '/strategies':
            self.send_json({'strategies': self.strategies[:100]})  # 限制返回数量

        elif path == '/predict':
            # 执行预测
            if self.executor:
                results = self.executor.predict_with_all(self.df)
                self.send_json({'predictions': results})
            else:
                self.send_json({'error': 'no strategies loaded'}, status=500)

        elif path == '/features':
            # 返回最新特征
            if self.fb:
                features = self.fb.compute_all_features(len(self.df))
                self.send_json({'features': features})
            else:
                self.send_json({'error': 'no data loaded'}, status=500)

        elif path == '/latest':
            # 返回最新开奖结果
            if len(self.df) > 0:
                latest = self.df.iloc[-1].to_dict()
                self.send_json({'latest': latest})
            else:
                self.send_json({'error': 'no data'}, status=500)

        else:
            self.send_json({'error': 'not found'}, status=404)

    def send_json(self, data, status=200):
        """发送JSON响应"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def log_message(self, format, *args):
        """自定义日志格式"""
        print(f"[API] {args[0]}")


def load_data():
    """加载数据"""
    with open('/home/admin1/liuhecai_standard_v2.json') as f:
        data = json.load(f)

    import pandas as pd
    df = pd.DataFrame(data)
    return df


def run_server(port=8080):
    """运行API服务器"""
    # 加载数据
    print("[启动] 加载数据...")
    df = load_data()

    # 加载策略
    print("[启动] 加载策略...")
    executor = StrategyExecutor('/home/admin1/liuhecai_strategy_search/strategies.json')

    # 创建特征构建器
    fb = FeatureBuilder(df)

    # 设置处理器
    APIHandler.df = df
    APIHandler.fb = fb
    APIHandler.executor = executor
    APIHandler.strategies = executor.strategies

    # 启动服务器
    server = HTTPServer(('0.0.0.0', port), APIHandler)
    print(f"[启动] API服务器运行在 http://0.0.0.0:{port}")
    print(f"  - GET /health - 健康检查")
    print(f"  - GET /strategies - 策略列表")
    print(f"  - GET /predict - 执行预测")
    print(f"  - GET /features - 最新特征")
    print(f"  - GET /latest - 最新开奖")

    server.serve_forever()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='策略搜索系统API')
    parser.add_argument('--port', '-p', type=int, default=8080, help='端口')
    args = parser.parse_args()

    run_server(args.port)