可以。这次我们把 **convention 从头固定下来**，不再混用不同论文的记号。

我下面采用最常见的一套：

[
[\hat x_i,\hat p_j]=i\delta_{ij},
\qquad
\hat x=\frac{\hat a+\hat a^\dagger}{\sqrt2},
\qquad
\hat p=\frac{\hat a-\hat a^\dagger}{i\sqrt2}.
]

于是单模真空的协方差是

[
V_{\rm vac}=\frac12 I_2.
]

我们把 (m) 模 Gaussian state 写成：

[
\boxed{\rho_G\leftrightarrow(\mathbf d,V)}
]

其中

[
\mathbf d=
\langle\hat{\mathbf r}\rangle,
\qquad
\hat{\mathbf r}
===============

(x_1,p_1,\ldots,x_m,p_m)^T.
]

下面从这里一路走到

[
P(n_1,\ldots,n_m).
]

---

# 一、总流程先给出来

整个计算链是：

[
\boxed{
(\mathbf d,V)
\rightarrow
(Q,\boldsymbol\alpha)
\rightarrow
(A,\boldsymbol\gamma)
\rightarrow
(A_{\mathbf n},\boldsymbol\gamma_{\mathbf n})
\rightarrow
B_{\mathbf n}
\rightarrow
\operatorname{lhaf}(B_{\mathbf n})
\rightarrow
P(\mathbf n)
}
]

其中：

* (V)：协方差矩阵
* (\mathbf d)：quadrature 均值
* (Q)：Q-matrix
* (\boldsymbol\alpha)：复数形式的 displacement
* (A)：二阶 Gaussian correlation matrix
* (\boldsymbol\gamma)：一阶 displacement contribution
* (A_{\mathbf n})：根据 photon pattern 扩展后的矩阵
* (B_{\mathbf n})：加入 loop 权重后的矩阵

最后使用 Loop Hafnian。

---

# 二、Step 1：输入均值和协方差

我们知道：

[
\boxed{
\mathbf d=
(d_{x_1},d_{p_1},\ldots,d_{x_m},d_{p_m})^T
}
]

以及：

[
\boxed{
V_{ij}
======

\frac12
\langle
\Delta r_i\Delta r_j+
\Delta r_j\Delta r_i
\rangle
}
]

这里 (V) 是 (2m\times2m)。

例如两模：

[
V=
\begin{pmatrix}
\langle x_1^2\rangle_c&
\langle{x_1,p_1}/2\rangle_c&
\cdots\
\cdots&&
\end{pmatrix}.
]

---

# 三、Step 2：构造 (Q)

定义：

[
\boxed{
Q=V+\frac12I_{2m}
}
]

这里的 (Q) 是 (2m\times2m)。

注意：

[
\boxed{Q\text{ 只由 }V\text{ 决定}}
]

均值 (\mathbf d) 不进入 (Q)。

---

# 四、Step 3：把 quadrature 均值转换成 complex displacement

对于每一个 mode：

[
\boxed{
\alpha_i=
\frac{d_{x_i}+id_{p_i}}{\sqrt2}
}
]

于是：

[
\boldsymbol\alpha
=================

(\alpha_1,\ldots,\alpha_m)^T.
]

例如单模 coherent state：

[
\alpha=\langle\hat a\rangle.
]

这与

[
d_x=\sqrt2\operatorname{Re}\alpha,
\qquad
d_p=\sqrt2\operatorname{Im}\alpha
]

一致。

---

# 五、Step 4：由 (Q) 得到 (A)

定义交换矩阵：

[
\boxed{
X=
\begin{pmatrix}
0&I_m\
I_m&0
\end{pmatrix}
}
]

然后：

[
\boxed{
A=X(I-Q^{-1})
}
]

这是 GBS 中非常核心的一步。

此时：

[
A\in\mathbb C^{2m\times2m}.
]

注意这里非常重要：

[
\boxed{A\text{ 的对角线一般不需要是 }0}
]

我们之前讨论的那个问题就在这里。

---

# 六、Step 5：由 (Q,\alpha) 得到 (\gamma)

在这一套 convention 下，定义：

[
\boxed{
\gamma=XQ^{-1}\boldsymbol\alpha^*
}
]

这里要注意：

[
\boldsymbol\alpha^*
]

是复共轭。

于是：

[
\gamma\in\mathbb C^{2m}.
]

因此到这里，我们已经把 Gaussian state：

[
(\mathbf d,V)
]

转换成：

[
\boxed{(A,\gamma)}.
]

这两个东西分别承担：

[
A\rightarrow\text{二阶 correlation}
]

[
\gamma\rightarrow\text{一阶 displacement}.
]

---

# 七、Step 6：为什么最终会出现 (A) 和 (\gamma)？

这是整个公式的核心。

Gaussian state 的 Fock-basis generating function 可以写成：

[
\boxed{
G(\mathbf z)
============

C
\exp
\left(
\frac12\mathbf z^TA\mathbf z
+
\gamma^T\mathbf z
\right)
}
]

其中归一化因子为：

[
\boxed{
C=
\frac{
\exp\left(
-\frac12
\boldsymbol\alpha^\dagger
Q^{-1}
\boldsymbol\alpha
\right)
}{
\sqrt{\det Q}
}
}
]

所以：

[
G(\mathbf z)
============

\frac{
e^{-\frac12\alpha^\dagger Q^{-1}\alpha}
}{
\sqrt{\det Q}
}
\exp
\left(
\frac12z^TAz+\gamma^Tz
\right).
]

这一步非常重要，因为接下来所有 Hafnian 都从这里产生。

---

# 八、Step 7：指定你想要的 photon pattern

假设：

[
\boxed{
\mathbf n=(n_1,n_2,\ldots,n_m)
}
]

总光子数：

[
\boxed{
N=\sum_{i=1}^{m}n_i
}
]

例如：

[
\mathbf n=(2,0,1,2)
]

那么：

[
N=5.
]

---

# 九、Step 8：根据 (\mathbf n) 构造 (A_{\mathbf n})

定义重复索引：

[
S_{\mathbf n}
=============

(
\underbrace{1,\ldots,1}*{n_1},
\underbrace{2,\ldots,2}*{n_2},
\ldots,
\underbrace{m,\ldots,m}_{n_m}
).
]

然后：

[
\boxed{
A_{\mathbf n}
=============

A[S_{\mathbf n},S_{\mathbf n}]
}
]

也就是：

> 根据 (n_i)，同时重复第 (i) 行和第 (i) 列。

---

# 十、这里要特别注意：(A) 是 (2m\times2m)

这也是前面讨论中最容易混淆的地方。

因为 (A) 是：

[
2m\times2m
]

而不是简单的：

[
m\times m.
]

这是由于我们使用了：

[
(x_1,p_1,\ldots,x_m,p_m)
]

的 quadrature 描述，并通过 (Q) 转到了 complex representation。

实际 GBS 软件/论文中，也常进一步把矩阵重新排列到

[
(a_1,\ldots,a_m,a_1^\dagger,\ldots,a_m^\dagger)
]

的形式。

**因此实际实现时一定要固定矩阵排列 convention。**

这是为什么不同资料里的 (A) 看起来有时是 (m\times m)，有时是 (2m\times2m)。

---

# 十一、Step 9：构造 (\gamma_{\mathbf n})

和 (A) 完全一样，根据 photon pattern 重复对应元素：

[
\boxed{
\gamma_{\mathbf n}
==================

\gamma[S_{\mathbf n}]
}
]

例如：

[
\mathbf n=(2,0,1,2)
]

则：

[
S_{\mathbf n}=(1,1,3,4,4)
]

于是：

[
\gamma_{\mathbf n}
==================

(\gamma_1,\gamma_1,\gamma_3,\gamma_4,\gamma_4)^T.
]

---

# 十二、Step 10：构造 Loop Hafnian 的矩阵

现在定义：

[
\boxed{
B_{\mathbf n}
=============

A_{\mathbf n}
\quad\text{with diagonal replaced by}\quad
\gamma_{\mathbf n}
}
]

也就是：

[
\boxed{
(B_{\mathbf n})_{ij}
====================

\begin{cases}
(A_{\mathbf n})*{ij},&i\neq j,[4pt]
(\gamma*{\mathbf n})_i,&i=j.
\end{cases}
}
]

这就是前面你追问的地方。

注意：

**不是把 (A_{\mathbf n}) 的对角线物理意义删除了。**

例如原来的：

[
A_{ii}
]

如果 (n_i\ge2)，经过重复索引以后，会出现在 (A_{\mathbf n}) 的非对角位置：

[
(A_{\mathbf n})*{jk}=A*{ii},
\qquad j\neq k.
]

它因此仍然参与 Hafnian/Loop Hafnian。

而真正放在 (B_{\mathbf n}) 对角线上的，是：

[
\gamma_i,
]

代表 single/loop contribution。

---

# 十三、Step 11：计算 Loop Hafnian

现在计算：

[
\boxed{
\operatorname{lhaf}(B_{\mathbf n})
}
]

Loop Hafnian 就是在所有节点之间考虑：

1. 两个不同节点之间的 pairing：

[
i\leftrightarrow j
]

贡献：

[
B_{ij}
]

2. 一个节点自己形成 loop：

[
i\rightarrow i
]

贡献：

[
B_{ii}=\gamma_i.
]

---

# 十四、Step 12：得到最终概率

最终：

[
\boxed{
P(n_1,\ldots,n_m)
=================

\frac{
\exp\left(
-\frac12
\boldsymbol\alpha^\dagger Q^{-1}\boldsymbol\alpha
\right)
}{
\sqrt{\det Q}
}
\frac{
\left|
\operatorname{lhaf}(B_{\mathbf n})
\right|^2
}{
n_1!n_2!\cdots n_m!
}
}
]

这就是在我们当前固定 convention 下的完整结构。

---

# 十五、现在把整个流程压缩成一条公式链

你可以把它记成：

[
\boxed{
(\mathbf d,V)
}
]

↓

[
Q=V+\frac12I
]

↓

[
\alpha_i=\frac{d_{x_i}+id_{p_i}}{\sqrt2}
]

↓

[
A=X(I-Q^{-1})
]

[
\gamma=XQ^{-1}\alpha^*
]

↓

给定：

[
\mathbf n=(n_1,\ldots,n_m)
]

↓

[
S_{\mathbf n}
=============

(1^{n_1},2^{n_2},\ldots,m^{n_m})
]

↓

[
A_{\mathbf n}=A[S_{\mathbf n},S_{\mathbf n}]
]

[
\gamma_{\mathbf n}=\gamma[S_{\mathbf n}]
]

↓

[
B_{\mathbf n}
=============

A_{\mathbf n}
\quad
\text{with}
\quad
\operatorname{diag}(B_{\mathbf n})=\gamma_{\mathbf n}
]

↓

[
\operatorname{lhaf}(B_{\mathbf n})
]

↓

[
\boxed{
P(\mathbf n)
============

\frac{
e^{-\frac12\alpha^\dagger Q^{-1}\alpha}
|\operatorname{lhaf}(B_{\mathbf n})|^2
}{
\sqrt{\det Q}\prod_i n_i!
}
}
]

---

# 十六、零均值情况现在自然出来了

如果：

[
\mathbf d=0
]

那么：

[
\alpha=0
]

因此：

[
\gamma=0.
]

于是：

[
B_{\mathbf n}
]

的对角线全为 0。

Loop Hafnian 就退化成普通 Hafnian：

[
\operatorname{lhaf}(B_{\mathbf n})
==================================

\operatorname{haf}(A_{\mathbf n}).
]

所以：

[
\boxed{
P(\mathbf n)
============

\frac{
|\operatorname{haf}(A_{\mathbf n})|^2
}{
\sqrt{\det Q}\prod_i n_i!
}
}
]

这就是我们之前讨论的标准 zero-displacement GBS 公式。

---

# 十七、一个最小例子：单模 coherent state

为了验证这套 convention，我们可以拿最简单的 coherent state 检查。

coherent state：

[
V=\frac12I
]

因此：

[
Q=I.
]

所以：

[
A=X(I-I)=0.
]

而：

[
\alpha\neq0.
]

因此：

[
\gamma=X\alpha^*.
]

对于 (n) 个光子，Loop Hafnian 只有全部使用 loops 的一种方式：

[
\operatorname{lhaf}(B_n)=\gamma^n.
]

最终得到 Poisson 型的 photon-number distribution：

[
P(n)
====

e^{-|\alpha|^2}
\frac{|\alpha|^{2n}}{n!}.
]

这正好是 coherent state 应有的结果。

所以这套结构是自洽的：

[
\boxed{
\text{coherent state}
\Rightarrow
A=0
\Rightarrow
\text{只有 loops}
}
]

而 squeezed vacuum 则是：

[
\boxed{
\text{squeezed vacuum}
\Rightarrow
\gamma=0
\Rightarrow
\text{只有 pairings}
}
]

这两个极限非常适合用来理解整个公式。

---

## 最后抓住三个核心对象

你现在学习 GBS 时，可以暂时只记住：

[
\boxed{Q=V+\frac12I}
]

负责把 Gaussian covariance 转换到 photon-number 计算所需的表示；

[
\boxed{A=X(I-Q^{-1})}
]

负责描述 **pairing（二阶关联）**；

[
\boxed{\gamma=XQ^{-1}\alpha^*}
]

负责描述 **single/loop（位移）**。

然后：

[
\boxed{
(A,\gamma)
\xrightarrow{\mathbf n}
B_{\mathbf n}
\xrightarrow{\operatorname{lhaf}}
P(\mathbf n)
}
]

这就是一般 Gaussian state → Fock measurement probability 的核心。

需要特别强调的是，**这里的 (A,Q,\alpha,\gamma) 的维度和排列必须全部保持同一 convention**；上面这一套是一个自洽的 convention，但不同 GBS 文献可能采用不同的 quadrature 排列或 (\hbar) 归一化，因此看到其他公式时不能直接逐项比较。([arXiv][1])

[1]: https://arxiv.org/abs/2010.15595?utm_source=chatgpt.com "Quadratic speedup for simulating Gaussian boson sampling"
