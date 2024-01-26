# coding:utf8

import torch
import torch.nn as nn
import numpy as np
import random
import json
import matplotlib.pyplot as plt

"""

基于pytorch的网络编写
实现一个网络完成一个简单nlp任务
判断文本中是否有某些特定字符出现
对比rnn和pooling做法
"""


class TorchModel(nn.Module):
    def __init__(self, x_dim, h_dim, sentence_length, vocab):
        super(TorchModel, self).__init__()
        self.embedding = nn.Embedding(len(vocab), x_dim)  # embedding层: 负责把字符串转换成矩阵

        # pool vs rnn
        # self.pool = nn.AvgPool1d(sentence_length)  # 池化层

        self.pool = nn.RNN(x_dim, h_dim, batch_first=True)
        self.classify = nn.Linear(x_dim, sentence_length+1)
        self.loss = nn.functional.cross_entropy

    # 当输入真实标签，返回loss值；无真实标签，返回预测值
    def forward(self, x, y=None):
        x = self.embedding(x)  # (batch_size, sen_len) -> (batch_size, sen_len, x_dim)

        # pool vs rnn
        # x = self.pool(x.transpose(1, 2)).squeeze()  # (batch_size, sen_len, x_dim) -> (batch_size, x_dim)
        _, hidden = self.pool(x)
        x = hidden.squeeze()
        y_pred = self.classify(x)
        if y is not None:
            return self.loss(y_pred, y)  # 预测值和真实值计算损失
        else:
            return y_pred  # 输出预测结果


# 字符集：随便挑了一些字，实际上还可以扩充
# 为每个字生成一个标号
# {"a":1, "b":2, "c":3...}
# abc -> [1,2,3]
def build_vocab(vocab_path):
    chars = "abcdefg"  # 字符集
    vocab = {"pad": 0}
    for index, char in enumerate(chars):
        vocab[char] = index + 1  # 每个字对应一个序号
    vocab['unk'] = len(vocab)

    # 保存词表
    writer = open(vocab_path, "w", encoding="utf8")
    writer.write(json.dumps(vocab, ensure_ascii=False, indent=2))
    writer.close()
    return vocab


# 模型
def build_model(x_dim, h_dim, sentence_length, vocab):
    return TorchModel(x_dim, h_dim, sentence_length, vocab)


# 优化器
def build_optimizer(model):
    learn_rate = 0.002  # 学习率
    return torch.optim.Adam(model.parameters(), lr=learn_rate)


# 训练
def training(model, model_path, optim, sentence_length, vocab):
    epoch_num = 20  # 训练轮数
    batch_size = 20  # 每次训练样本个数
    train_sample = 1000  # 每轮训练总共训练的样本总数

    log = []
    for epoch in range(epoch_num):
        model.train()
        watch_loss = []
        for batch in range(int(train_sample / batch_size)):
            # 创建训练集
            x, y = build_dataset(batch_size, sentence_length, vocab)  # 构造一组训练样本
            optim.zero_grad()  # 梯度归零
            loss = model(x, y)  # 计算loss
            loss.backward()  # 计算梯度
            optim.step()  # 更新权重
            watch_loss.append(loss.item())
        print("第%d轮平均loss:%f" % (epoch + 1, np.mean(watch_loss)))
        acc = evaluate(model, sentence_length, vocab)  # 测试本轮模型结果
        log.append([acc, np.mean(watch_loss)])

    # 保存模型
    torch.save(model.state_dict(), model_path)
    return log


# 测试：测试每轮模型的准确率
def evaluate(model, sample_length, vocab):
    model.eval()
    x, y = build_dataset(200, sample_length, vocab)  # 建立200个用于测试的样本
    correct, wrong = 0, 0
    with torch.no_grad():
        y_pred = model(x)  # 模型预测
        for y_p, y_t in zip(y_pred, y):  # 与真实标签进行对比
            if int(torch.argmax(y_p)) == int(y_t):
                correct += 1
            else:
                wrong += 1
    print("evaluate本轮预测集中共有%d个正样本，%d个负样本, 正确预测个数：%d, 正确率：%f" % (sum(y), 200 - sum(y), correct, correct / (correct + wrong)))
    return correct / (correct + wrong)


# 建立数据集
# 输入需要的样本数量。需要多少生成多少
def build_dataset(sample_length, sentence_length, vocab):
    dataset_x = []
    dataset_y = []
    for i in range(sample_length):
        x, y = build_sample(vocab, sentence_length)
        dataset_x.append(x)
        dataset_y.append(y)
    return torch.LongTensor(dataset_x), torch.LongTensor(dataset_y)


# 随机生成一个样本
# 从所有字中选取sentence_length个字
# 反之为负样本
def build_sample(vocab, sentence_length):
    # 随机从字表选取sentence_length个字，可能重复
    x = [random.choice(list(vocab.keys())) for _ in range(sentence_length)]
    # 指定哪些字出现时为正样本
    if set("ac") & set(x):
        y = 1
    # 指定字都未出现，则为负样本
    else:
        y = 0
    x = [vocab.get(word, vocab['unk']) for word in x]  # 将字转换成序号，为了做embedding
    return x, y


# 画图
def plot(log):
    # print("log:", log)
    plt.plot(range(len(log)), [l[0] for l in log], label="acc")  # 画acc曲线
    plt.plot(range(len(log)), [l[1] for l in log], label="loss")  # 画loss曲线
    plt.legend()
    plt.show()


# 预测：使用训练好的模型做预测
def predict(x_dim, h_dim, model_path, vocab_path, input_strs):
    sentence_length = 6  # 样本文本长度
    vocab = json.load(open(vocab_path, "r", encoding="utf8"))  # 加载字符表
    model = build_model(x_dim, h_dim, sentence_length, vocab)  # 建立模型
    model.load_state_dict(torch.load(model_path))  # 加载训练好的权重

    x = []
    for input_string in input_strs:
        x.append([vocab[char] for char in input_string])  # 将输入序列化

    model.eval()  # 测试模式
    with torch.no_grad():  # 不计算梯度
        result = model.forward(torch.LongTensor(x))  # 模型预测
    for i, input_string in enumerate(input_strs):
        print("输入：%s, 预测类别：%s, 概率值：%s" % (input_string, torch.argmax(result[i]), result[i]))  # 打印结果


def main():
    # 配置
    model_path = "model.pth"
    vocab_path = "vocab.json"
    x_dim = 20  # 每个字的维度
    h_dim = 20
    sentence_length = 6  # 样本文本长度

    test_strs = ["ffafee", "ggbdfg", "eecdbg", "ggeeaa"]

    # 字表
    vocab = build_vocab(vocab_path)

    # 模型
    model = build_model(x_dim, h_dim, sentence_length, vocab)

    # 优化器
    optim = build_optimizer(model)

    # 训练
    log = training(model, model_path, optim, sentence_length, vocab)

    # 画图
    # plot(log)

    # 预测
    predict(x_dim, h_dim, model_path, vocab_path, test_strs)
    return


if __name__ == "__main__":
    main()
