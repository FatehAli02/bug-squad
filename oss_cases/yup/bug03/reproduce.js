// Original Bug Squad reproduction with synthetic inputs.
import assert from 'node:assert/strict';
import { create as mixed } from './upstream/src/mixed';

const combined = mixed().label('Quantity').meta({ section: 'inventory' }).concat(mixed());
const description = combined.describe();
assert.equal(description.label, 'Quantity');
assert.deepEqual(description.meta, { section: 'inventory' });
