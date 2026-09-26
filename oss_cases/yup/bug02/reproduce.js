// Original Bug Squad reproduction with synthetic inputs.
import assert from 'node:assert/strict';
import array from './upstream/src/array';

assert.deepEqual(array().ensure().cast(23), [23]);
