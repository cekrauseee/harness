import { computeLayout, ranks } from './layout'

it('lays out a dependency cycle instead of recursing forever', () => {
  const ids = ['a', 'b', 'c']
  const edges: [string, string][] = [
    ['a', 'b'],
    ['b', 'c'],
    ['c', 'a'],
  ]
  expect(Object.values(ranks(ids, edges)).sort()).toEqual([0, 1, 2])
  const pos = computeLayout(ids, edges, { a: 80, b: 80, c: 80 })
  expect(Object.keys(pos).sort()).toEqual(ids)
})
