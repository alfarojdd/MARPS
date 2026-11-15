/// <reference types="node" />
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { manualMission, nextPick, pointLabel, toPlannerPoint } from './picking.ts'
import type { Place } from './types'

const place = (name: string, lon: number, lat: number): Place => ({ name, lon, lat, col: 0, row: 0 })
const a = place('A', 77.451234, 18.443211)
const b = place('B', 77.3, 18.5)

test('pointLabel formats lat then lon', () => {
  assert.equal(pointLabel(77.45123, 18.44321), '18.4432°N 77.4512°E')
})

test('toPlannerPoint gives lon,lat with 5 decimals', () => {
  assert.equal(toPlannerPoint(a), '77.45123,18.44321')
})

test('nextPick sets origin when nothing is picked', () => {
  assert.deepEqual(nextPick({ origin: null, destination: null }, a), { origin: a, destination: null })
})

test('nextPick sets destination when only origin is picked', () => {
  assert.deepEqual(nextPick({ origin: a, destination: null }, b), { origin: a, destination: b })
})

test('nextPick restarts when both are picked', () => {
  assert.deepEqual(nextPick({ origin: a, destination: b }, b), { origin: b, destination: null })
})

test('manualMission uses planner defaults', () => {
  assert.deepEqual(manualMission(a, b), {
    human: true,
    origin: '77.45123,18.44321',
    destination: '77.30000,18.50000',
    power: false,
    route_preference: null,
    safety: 'normal',
    science_targets: [],
    science_detour: 'medium',
    return_to_origin: false,
  })
})
