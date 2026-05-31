#!/usr/bin/env python3
"""
遗传算法引擎 (DEAP)
===================

使用DEAP库实现策略进化：
- 选择
- 交叉
- 突变
- 精英保留

参数：
- population: 300
- mutation: 0.1
- crossover: 0.7
- elite: 0.05
"""

import random
import numpy as np
from typing import List, Tuple, Callable, Dict
from dataclasses import dataclass
import json

# 尝试导入DEAP，如果不可用则使用自定义实现
try:
    from deap import base, creator, tools, algorithms
    DEAP_AVAILABLE = True
except ImportError:
    DEAP_AVAILABLE = False
    print("[警告] DEAP未安装，使用自定义遗传算法")


ZODIACS = ['鼠', '牛', '虎', '兔', '龍', '蛇', '马', '羊', '猴', '雞', '狗', '豬']
COLORS = ['red', 'blue', 'green']


@dataclass
class GAParams:
    """遗传算法参数"""
    population: int = 300
    generations: int = 20
    mutation_rate: float = 0.1
    crossover_rate: float = 0.7
    elite_rate: float = 0.05
    tournament_size: int = 5


class StrategyIndividual:
    """策略个体"""

    def __init__(self, strategy_id: str = ""):
        self.id = strategy_id or f"ind_{random.randint(10000, 99999)}"
        self.weights = self._generate_random_weights()
        self.fitness = 0.0
        self.generation = 0

    def _generate_random_weights(self) -> Dict[str, float]:
        """生成随机权重"""
        weights = {}

        # 遗漏权重
        for z in ZODIACS:
            weights[f'gap_{z}'] = random.random() * 3

        # 频率权重
        for window in [10, 20, 50]:
            for z in ZODIACS:
                weights[f'freq_{window}_{z}'] = random.random()

        # 连出权重
        for z in ZODIACS:
            weights[f'streak_{z}'] = random.random()

        # 波色权重
        for color in COLORS:
            weights[f'color_freq_10_{color}'] = random.random() * 5

        return weights

    def predict(self, features: Dict) -> List[str]:
        """根据权重预测六肖"""
        scores = {}

        for z in ZODIACS:
            score = 0

            # 遗漏
            gap_key = f'gap_{z}'
            if gap_key in self.weights:
                score += features.get(gap_key, 0) * self.weights[gap_key]

            # 频率
            for window in [10, 20, 50]:
                freq_key = f'freq_{window}_{z}'
                if freq_key in self.weights:
                    score += features.get(freq_key, 0) * self.weights[freq_key]

            # 连出
            streak_key = f'streak_{z}'
            if streak_key in self.weights:
                streak = features.get(streak_key, 0)
                score += max(0, 10 - streak) * self.weights[streak_key]

            # 波色
            for color in COLORS:
                color_key = f'color_freq_10_{color}'
                if color_key in self.weights:
                    score += features.get(color_key, 0) * self.weights[color_key]

            scores[z] = score

        sorted_z = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [z for z, s in sorted_z[:6]]

    def mutate(self, rate: float = 0.1):
        """突变"""
        if random.random() < rate:
            keys = list(self.weights.keys())
            key = random.choice(keys)
            self.weights[key] = random.random()

    def crossover(self, other: 'StrategyIndividual') -> 'StrategyIndividual':
        """交叉"""
        child = StrategyIndividual()
        child.weights = {}

        for k in self.weights:
            if random.random() < 0.5:
                child.weights[k] = self.weights[k]
            else:
                child.weights[k] = other.weights[k]

        child.generation = max(self.generation, other.generation) + 1
        return child

    def copy(self) -> 'StrategyIndividual':
        """深拷贝"""
        new_ind = StrategyIndividual()
        new_ind.weights = self.weights.copy()
        new_ind.fitness = self.fitness
        new_ind.generation = self.generation
        return new_ind

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'generation': self.generation,
            'fitness': self.fitness,
            'weights': {k: round(v, 4) for k, v in self.weights.items()}
        }


class CustomGAEngine:
    """自定义遗传算法引擎（当DEAP不可用时）"""

    def __init__(self, fitness_func: Callable, params: GAParams = None):
        self.params = params or GAParams()
        self.fitness_func = fitness_func
        self.population = []
        self.generation = 0
        self.history = []

    def init_population(self, size: int = None):
        """初始化种群"""
        size = size or self.params.population
        self.population = [StrategyIndividual() for _ in range(size)]
        print(f"[GA] 初始化种群: {size} 个")

    def evaluate(self, verbose: bool = False) -> List[Tuple[StrategyIndividual, float]]:
        """评估所有个体"""
        results = []
        for i, ind in enumerate(self.population):
            fitness = self.fitness_func(ind)
            ind.fitness = fitness
            results.append((ind, fitness))

            if verbose and (i + 1) % 50 == 0:
                print(f"  评估进度: {i+1}/{len(self.population)}")

        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def select(self, evaluated: List[Tuple], n: int) -> List[StrategyIndividual]:
        """锦标赛选择"""
        selected = []
        for _ in range(n):
            tournament = random.sample(evaluated, min(self.params.tournament_size, len(evaluated)))
            winner = max(tournament, key=lambda x: x[1])[0]
            selected.append(winner.copy())
        return selected

    def evolve(self) -> List[StrategyIndividual]:
        """执行一代进化"""
        # 评估
        evaluated = self.evaluate(verbose=False)
        self.history.append((self.generation, max(x[1] for x in evaluated)))

        # 精英保留
        n_elite = int(self.params.population * self.params.elite_rate)
        elite = [ind.copy() for ind, _ in evaluated[:n_elite]]

        # 选择
        selected = self.select(evaluated, self.params.population - n_elite)

        # 交叉突变
        new_population = elite.copy()
        while len(new_population) < self.params.population:
            if len(selected) >= 2:
                p1, p2 = random.sample(selected, 2)

                # 交叉
                if random.random() < self.params.crossover_rate:
                    child = p1.crossover(p2)
                else:
                    child = p1.copy()

                # 突变
                child.mutate(self.params.mutation_rate)

                new_population.append(child)

        self.population = new_population[:self.params.population]
        self.generation += 1

        # 显示TOP3
        top3 = evaluated[:3]
        print(f"[GA] Gen {self.generation}: TOP3 = {top3[0][1]:.4f}, {top3[1][1]:.4f}, {top3[2][1]:.4f}")

        return [ind for ind, _ in evaluated[:10]]

    def run(self, n_generations: int = None) -> List[StrategyIndividual]:
        """运行遗传算法"""
        n_generations = n_generations or self.params.generations

        print(f"[GA] 开始进化: {n_generations} 代, 种群 {self.params.population}")

        for gen in range(n_generations):
            top_individuals = self.evolve()
            if gen == 0:
                self.best_so_far = top_individuals[0] if top_individuals else None
            elif top_individuals and top_individuals[0].fitness > self.best_so_far.fitness:
                self.best_so_far = top_individuals[0]

        print(f"[GA] 进化完成, 最佳: {self.best_so_far.fitness:.4f}")

        return self.get_best(n=50)

    def get_best(self, n: int = 50) -> List[StrategyIndividual]:
        """获取最佳个体"""
        evaluated = self.evaluate()
        return [ind for ind, _ in evaluated[:n]]


class DEAPGAEngine:
    """DEAP实现的遗传算法引擎"""

    def __init__(self, fitness_func: Callable, params: GAParams = None):
        self.params = params or GAParams()
        self.fitness_func = fitness_func
        self.toolbox = base.Toolbox()
        self.population = None
        self.generation = 0

        self._setup_deap()

    def _setup_deap(self):
        """设置DEAP"""
        if not DEAP_AVAILABLE:
            raise ImportError("DEAP not available")

        # 定义适应度函数（最大化）
        creator.create("FitnessMax", base.Fitness, weights=(1.0,))
        creator.create("Individual", list, fitness=creator.FitnessMax)

        # 注册操作
        self.toolbox.register("attr_float", random.random)
        self.toolbox.register("individual", self._create_individual)
        self.toolbox.register("population", self._create_population)
        self.toolbox.register("evaluate", self._evaluate_individual)
        self.toolbox.register("mate", self._cx_individual)
        self.toolbox.register("mutate", self._mut_individual)
        self.toolbox.register("select", tools.selTournament, tournsize=self.params.tournament_size)
        self.toolbox.register("clone", self._clone_individual)

    def _clone_individual(self, ind):
        """深拷贝个体"""
        import copy
        new_ind = copy.deepcopy(ind)
        return new_ind

    def init_population(self, size: int = None):
        """初始化种群"""
        size = size or self.params.population
        self.population = self.toolbox.population(n=size)
        print(f"[GA] 初始化种群: {size} 个")

    def _create_individual(self):
        """创建个体"""
        ind = StrategyIndividual()
        return creator.Individual(list(ind.weights.values()))

    def _create_population(self, n):
        """创建种群"""
        return [self.toolbox.individual() for _ in range(n)]

    def _evaluate_individual(self, individual):
        """评估个体"""
        # 构建临时策略
        ind_obj = StrategyIndividual()
        keys = list(ind_obj.weights.keys())
        for i, k in enumerate(keys):
            if i < len(individual):
                ind_obj.weights[k] = individual[i]

        return (self.fitness_func(ind_obj),)

    def _cx_individual(self, ind1, ind2):
        """交叉"""
        keys = list(StrategyIndividual().weights.keys())
        for i in range(min(len(ind1), len(ind2))):
            if random.random() < self.params.crossover_rate:
                ind1[i], ind2[i] = ind2[i], ind1[i]
        return ind1, ind2

    def _mut_individual(self, ind):
        """突变"""
        for i in range(len(ind)):
            if random.random() < self.params.mutation_rate:
                ind[i] = random.random()
        return ind,

    def run(self, n_generations: int = None) -> List[StrategyIndividual]:
        """运行DEAP遗传算法"""
        if not DEAP_AVAILABLE:
            raise ImportError("DEAP not available")

        n_generations = n_generations or self.params.generations

        # 使用已初始化的种群，或创建新的
        if self.population is None:
            self.population = self.toolbox.population(n=self.params.population)

        # 评估初始种群
        fitnesses = list(map(self.toolbox.evaluate, self.population))
        for ind, fit in zip(self.population, fitnesses):
            ind.fitness = fit

        print(f"[DEAP GA] 开始进化: {n_generations} 代, 种群 {self.params.population}")

        for gen in range(n_generations):
            # 选择
            offspring = self.toolbox.select(self.population, len(self.population))

            # 克隆
            offspring = list(map(self.toolbox.clone, offspring))

            # 交叉
            for child1, child2 in zip(offspring[::2], offspring[1::2]):
                if len(offspring) > 1:
                    self.toolbox.mate(child1, child2)

            # 突变
            for i, mutant in enumerate(offspring):
                offspring[i] = self.toolbox.mutate(mutant)[0]

            # 评估
            fitnesses = map(self.toolbox.evaluate, offspring)
            for ind, fit in zip(offspring, fitnesses):
                ind.fitness = fit

            # 选择最佳
            self.population = offspring

            # 输出进度
            fits = [ind.fitness[0] for ind in self.population]
            best = max(fits)
            print(f"[DEAP GA] Gen {gen+1}: Best = {best:.4f}, Avg = {np.mean(fits):.4f}")

            self.generation = gen + 1

        # 返回最佳个体
        fits = [ind.fitness[0] for ind in self.population]
        best_idx = fits.index(max(fits))
        best_ind = self.population[best_idx]

        # 转换为StrategyIndividual列表
        results = []
        sorted_pop = sorted(zip(self.population, fits), key=lambda x: x[0], reverse=True)

        for ind, fit in sorted_pop[:50]:
            ind_obj = StrategyIndividual()
            keys = list(ind_obj.weights.keys())
            for i, k in enumerate(keys):
                if i < len(ind):
                    ind_obj.weights[k] = ind[i]
            ind_obj.fitness = fit
            results.append(ind_obj)

        return results


def create_ga_engine(fitness_func: Callable, params: GAParams = None) -> any:
    """工厂函数：创建GA引擎"""
    if DEAP_AVAILABLE:
        return DEAPGAEngine(fitness_func, params)
    else:
        return CustomGAEngine(fitness_func, params)


# ============ 测试 ============
if __name__ == '__main__':
    import pandas as pd

    # 加载数据
    with open('/home/admin1/liuhecai_standard_v2.json') as f:
        data = json.load(f)

    df = pd.DataFrame(data)
    print(f"数据: {len(df)} 条")

    # 测试遗传算法
    def mock_fitness(ind: StrategyIndividual) -> float:
        """模拟适应度函数"""
        return random.random()

    params = GAParams(population=50, generations=5)
    engine = create_ga_engine(mock_fitness, params)

    print("\n测试遗传算法:")
    results = engine.run(3)

    print(f"\n进化完成, 获得 {len(results)} 个策略")