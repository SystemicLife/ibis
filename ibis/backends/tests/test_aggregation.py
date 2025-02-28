import numpy as np
import pandas as pd
import pytest
from pytest import mark, param

import ibis.expr.datatypes as dt
from ibis.udf.vectorized import reduction


@reduction(input_type=[dt.double], output_type=dt.double)
def mean_udf(s):
    return s.mean()


aggregate_test_params = [
    param(
        lambda t: t.double_col.mean(),
        lambda s: s.mean(),
        'double_col',
        id='mean',
    ),
    param(
        lambda t: mean_udf(t.double_col),
        lambda s: s.mean(),
        'double_col',
        id='mean_udf',
        marks=[
            pytest.mark.notimpl(
                ["datafusion", "postgres", "clickhouse", "impala", "duckdb"]
            ),
            pytest.mark.never(["sqlite", "mysql"], reason="no udf support"),
        ],
    ),
    param(
        lambda t: t.double_col.min(),
        lambda s: s.min(),
        'double_col',
        id='min',
    ),
    param(
        lambda t: t.double_col.max(),
        lambda s: s.max(),
        'double_col',
        id='max',
    ),
    param(
        lambda t: (t.double_col + 5).sum(),
        lambda s: (s + 5).sum(),
        'double_col',
        id='complex_sum',
    ),
    param(
        lambda t: t.timestamp_col.max(),
        lambda s: s.max(),
        'timestamp_col',
        id='timestamp_max',
    ),
]


@pytest.mark.parametrize(
    ('result_fn', 'expected_fn', 'expected_col'),
    aggregate_test_params,
)
def test_aggregate(
    backend, alltypes, df, result_fn, expected_fn, expected_col
):
    expr = alltypes.aggregate(tmp=result_fn)
    result = expr.execute()

    # Create a single-row single-column dataframe with the Pandas `agg` result
    # (to match the output format of Ibis `aggregate`)
    expected = pd.DataFrame({'tmp': [df[expected_col].agg(expected_fn)]})

    backend.assert_frame_equal(result, expected)


@pytest.mark.parametrize(
    ('result_fn', 'expected_fn', 'expected_col'),
    aggregate_test_params,
)
def test_aggregate_grouped(
    backend, alltypes, df, result_fn, expected_fn, expected_col
):
    grouping_key_col = 'bigint_col'

    # Two (equivalent) variations:
    #  1) `groupby` then `aggregate`
    #  2) `aggregate` with `by`
    expr1 = alltypes.groupby(grouping_key_col).aggregate(tmp=result_fn)
    expr2 = alltypes.aggregate(tmp=result_fn, by=grouping_key_col)
    result1 = expr1.execute()
    result2 = expr2.execute()

    # Note: Using `reset_index` to get the grouping key as a column
    expected = (
        df.groupby(grouping_key_col)[expected_col]
        .agg(expected_fn)
        .rename('tmp')
        .reset_index()
    )

    # Row ordering may differ depending on backend, so sort on the
    # grouping key
    result1 = result1.sort_values(by=grouping_key_col).reset_index(drop=True)
    result2 = result2.sort_values(by=grouping_key_col).reset_index(drop=True)
    expected = expected.sort_values(by=grouping_key_col).reset_index(drop=True)

    backend.assert_frame_equal(result1, expected)
    backend.assert_frame_equal(result2, expected)


@pytest.mark.parametrize(
    ('result_fn', 'expected_fn'),
    [
        param(
            lambda t, where: t.bool_col.count(where=where),
            lambda t, where: len(t.bool_col[where].dropna()),
            id='count',
        ),
        param(
            lambda t, _: t.bool_col.any(),
            lambda t, _: t.bool_col.any(),
            id='any',
        ),
        param(
            lambda t, _: t.bool_col.notany(),
            lambda t, _: ~t.bool_col.any(),
            id='notany',
        ),
        param(
            lambda t, _: -t.bool_col.any(),
            lambda t, _: ~t.bool_col.any(),
            id='any_negate',
        ),
        param(
            lambda t, _: t.bool_col.all(),
            lambda t, _: t.bool_col.all(),
            id='all',
        ),
        param(
            lambda t, _: t.bool_col.notall(),
            lambda t, _: ~t.bool_col.all(),
            id='notall',
        ),
        param(
            lambda t, _: -t.bool_col.all(),
            lambda t, _: ~t.bool_col.all(),
            id='all_negate',
        ),
        param(
            lambda t, where: t.double_col.sum(where=where),
            lambda t, where: t.double_col[where].sum(),
            id='sum',
        ),
        param(
            lambda t, where: t.double_col.mean(where=where),
            lambda t, where: t.double_col[where].mean(),
            id='mean',
        ),
        param(
            lambda t, where: t.double_col.min(where=where),
            lambda t, where: t.double_col[where].min(),
            id='min',
        ),
        param(
            lambda t, where: t.double_col.max(where=where),
            lambda t, where: t.double_col[where].max(),
            id='max',
        ),
        param(
            lambda t, where: t.double_col.std(how='sample', where=where),
            lambda t, where: t.double_col[where].std(ddof=1),
            id='std',
        ),
        param(
            lambda t, where: t.double_col.var(how='sample', where=where),
            lambda t, where: t.double_col[where].var(ddof=1),
            id='var',
        ),
        param(
            lambda t, where: t.double_col.std(how='pop', where=where),
            lambda t, where: t.double_col[where].std(ddof=0),
            id='std_pop',
        ),
        param(
            lambda t, where: t.double_col.var(how='pop', where=where),
            lambda t, where: t.double_col[where].var(ddof=0),
            id='var_pop',
        ),
        param(
            lambda t, where: t.double_col.cov(t.float_col, where=where),
            lambda t, where: t.double_col[where].cov(t.float_col[where]),
            id='covar',
            marks=[
                pytest.mark.notimpl(
                    [
                        "clickhouse",
                        "dask",
                        "duckdb",
                        "impala",
                        "mysql",
                        "pandas",
                        "postgres",
                        "pyspark",
                        "sqlite",
                    ]
                )
            ],
        ),
        param(
            lambda t, where: t.double_col.corr(t.float_col, where=where),
            lambda t, where: t.double_col[where].corr(t.float_col[where]),
            id='corr',
            marks=[
                pytest.mark.notimpl(
                    [
                        "clickhouse",
                        "dask",
                        "duckdb",
                        "impala",
                        "mysql",
                        "pandas",
                        "postgres",
                        "pyspark",
                        "sqlite",
                    ]
                )
            ],
        ),
        param(
            lambda t, where: t.string_col.approx_nunique(where=where),
            lambda t, where: t.string_col[where].nunique(),
            id='approx_nunique',
        ),
        param(
            lambda t, where: t.double_col.arbitrary(how='first', where=where),
            lambda t, where: t.double_col[where].iloc[0],
            id='arbitrary_first',
            marks=pytest.mark.notimpl(
                ['impala', 'postgres', 'mysql', 'sqlite']
            ),
        ),
        param(
            lambda t, where: t.double_col.arbitrary(how='last', where=where),
            lambda t, where: t.double_col[where].iloc[-1],
            id='arbitrary_last',
            marks=pytest.mark.notimpl(
                ['impala', 'postgres', 'mysql', 'sqlite']
            ),
        ),
        param(
            lambda t, where: t.double_col.arbitrary(how='heavy', where=where),
            lambda t, where: t.double_col[where].iloc[8],
            id='arbitrary_heavy',
            # only clickhouse implements this option
            marks=pytest.mark.notimpl(
                [
                    "dask",
                    "datafusion",
                    "duckdb",
                    "impala",
                    "mysql",
                    "pandas",
                    "postgres",
                    "pyspark",
                    "sqlite",
                ],
            ),
        ),
        param(
            lambda t, where: t.bigint_col.bit_and(where=where),
            lambda t, where: np.bitwise_and.reduce(t.bigint_col[where].values),
            id='bit_and',
            marks=[
                pytest.mark.notimpl(["dask"]),
                pytest.mark.notyet(["impala", "pyspark"]),
            ],
        ),
        param(
            lambda t, where: t.bigint_col.bit_or(where=where),
            lambda t, where: np.bitwise_or.reduce(t.bigint_col[where].values),
            id='bit_or',
            marks=[
                pytest.mark.notimpl(["dask"]),
                pytest.mark.notyet(["impala", "pyspark"]),
            ],
        ),
        param(
            lambda t, where: t.bigint_col.bit_xor(where=where),
            lambda t, where: np.bitwise_xor.reduce(t.bigint_col[where].values),
            id='bit_xor',
            marks=[
                pytest.mark.notimpl(["dask"]),
                pytest.mark.notyet(["impala", "pyspark"]),
            ],
        ),
    ],
)
@pytest.mark.parametrize(
    ('ibis_cond', 'pandas_cond'),
    [
        param(lambda _: None, lambda _: slice(None), id='no_cond'),
        param(
            lambda t: t.string_col.isin(['1', '7']),
            lambda t: t.string_col.isin(['1', '7']),
            id='is_in',
        ),
    ],
)
@mark.notimpl(["datafusion"])
def test_reduction_ops(
    alltypes,
    df,
    result_fn,
    expected_fn,
    ibis_cond,
    pandas_cond,
):
    expr = result_fn(alltypes, ibis_cond(alltypes))
    result = expr.execute()

    expected = expected_fn(df, pandas_cond(df))
    np.testing.assert_allclose(result, expected)


@pytest.mark.notimpl(
    [
        "dask",
        "datafusion",
        "mysql",
        "pandas",
        "postgres",
        "sqlite",
    ]
)
def test_approx_median(alltypes):
    expr = alltypes.double_col.approx_median()
    result = expr.execute()
    assert isinstance(result, float)


@pytest.mark.parametrize(
    ('result_fn', 'expected_fn'),
    [
        param(
            lambda t, where: (
                t.groupby('bigint_col')
                .aggregate(
                    tmp=lambda t: t.string_col.group_concat(',', where=where)
                )
                .sort_by('bigint_col')
            ),
            lambda t, where: (
                (
                    t.assign(string_col=t.string_col.where(where))
                    if not isinstance(where, slice)
                    else t
                )
                .groupby('bigint_col')
                .string_col.agg(
                    lambda s: (
                        np.nan if pd.isna(s).all() else ','.join(s.values)
                    )
                )
                .rename('tmp')
                .sort_index()
                .reset_index()
            ),
            id='group_concat',
        )
    ],
)
@pytest.mark.parametrize(
    ('ibis_cond', 'pandas_cond'),
    [
        param(lambda _: None, lambda _: slice(None), id='no_cond'),
        param(
            lambda t: t.string_col.isin(['1', '7']),
            lambda t: t.string_col.isin(['1', '7']),
            marks=pytest.mark.notimpl(["dask", "pandas"]),
            id='is_in',
        ),
    ],
)
@mark.notimpl(["datafusion"])
def test_group_concat(
    backend,
    alltypes,
    df,
    result_fn,
    expected_fn,
    ibis_cond,
    pandas_cond,
):
    expr = result_fn(alltypes, ibis_cond(alltypes))
    result = expr.execute()
    expected = expected_fn(df, pandas_cond(df))

    backend.assert_frame_equal(result, expected)


@pytest.mark.parametrize(
    ('result_fn', 'expected_fn'),
    [
        param(
            lambda t: t.string_col.topk(3),
            lambda t: t.groupby('string_col')['string_col'].count().head(3),
            id='string_col_top3',
        )
    ],
)
@mark.notimpl(["pandas", "dask"])
@pytest.mark.notyet(["pyspark", "datafusion"])
def test_topk_op(alltypes, df, result_fn, expected_fn):
    # TopK expression will order rows by "count" but each backend
    # can have different result for that.
    # Note: Maybe would be good if TopK could order by "count"
    # and the field used by TopK
    t = alltypes.sort_by(alltypes.string_col)
    df = df.sort_values('string_col')
    result = result_fn(t).execute()
    expected = expected_fn(df)
    assert all(result['count'].values == expected.values)


@pytest.mark.parametrize(
    ('result_fn', 'expected_fn'),
    [
        param(
            lambda t: t[t.string_col.topk(3)],
            lambda t: t[
                t.string_col.isin(
                    t.groupby('string_col')['string_col'].count().head(3).index
                )
            ],
            id='string_col_filter_top3',
        )
    ],
)
@mark.notimpl(["datafusion", "pandas", "dask"])
def test_topk_filter_op(alltypes, df, result_fn, expected_fn):
    # TopK expression will order rows by "count" but each backend
    # can have different result for that.
    # Note: Maybe would be good if TopK could order by "count"
    # and the field used by TopK
    t = alltypes.sort_by(alltypes.string_col)
    df = df.sort_values('string_col')
    expr = result_fn(t)
    result = expr.execute()
    expected = expected_fn(df)
    assert result.shape[0] == expected.shape[0]


@pytest.mark.parametrize(
    'agg_fn',
    [
        param(lambda s: list(s), id='agg_to_list'),
        param(lambda s: np.array(s), id='agg_to_ndarray'),
    ],
)
@mark.notimpl(
    [
        "clickhouse",
        "datafusion",
        "duckdb",
        "impala",
        "mysql",
        "postgres",
        "sqlite",
    ]
)
def test_aggregate_list_like(backend, alltypes, df, agg_fn):
    """Tests .aggregate() where the result of an aggregation is a list-like.

    We expect the list / np.array to be treated as a scalar (in other words,
    the resulting table expression should have one element, which is the
    list / np.array).
    """

    udf = reduction(input_type=[dt.double], output_type=dt.Array(dt.double))(
        agg_fn
    )

    expr = alltypes.aggregate(result_col=udf(alltypes.double_col))
    result = expr.execute()

    # Expecting a 1-row DataFrame
    expected = pd.DataFrame({'result_col': [agg_fn(df.double_col)]})

    backend.assert_frame_equal(result, expected)


@mark.notimpl(
    [
        "clickhouse",
        "datafusion",
        "duckdb",
        "impala",
        "mysql",
        "postgres",
        "sqlite",
    ]
)
def test_aggregate_mixed(backend, alltypes, df):
    """Tests .aggregate() with multiple aggregations with mixed result types.

    (In particular, one aggregation that results in an array, and other
    aggregation(s) that result in a non-array)
    """

    @reduction(input_type=[dt.double], output_type=dt.double)
    def sum_udf(v):
        return np.sum(v)

    @reduction(input_type=[dt.double], output_type=dt.Array(dt.double))
    def collect_udf(v):
        return np.array(v)

    expr = alltypes.aggregate(
        sum_col=sum_udf(alltypes.double_col),
        collect_udf=collect_udf(alltypes.double_col),
    )
    result = expr.execute()

    expected = pd.DataFrame(
        {
            'sum_col': [sum_udf.func(df.double_col)],
            'collect_udf': [collect_udf.func(df.double_col)],
        }
    )

    backend.assert_frame_equal(result, expected, check_like=True)


@pytest.mark.notimpl(["datafusion", "pyspark"])
def test_binds_are_cast(alltypes):
    expr = alltypes.aggregate(
        high_line_count=(
            alltypes.string_col.case().when('1-URGENT', 1).else_(0).end().sum()
        )
    )

    expr.execute()


def test_agg_sort(alltypes):
    query = alltypes.aggregate(count=alltypes.count())
    query = query.sort_by(alltypes.year)
    query.execute()
