// Original Bug Squad reproduction with synthetic inputs.
import assert from 'node:assert/strict';
import { create as object } from './upstream/src/object';
import { create as string } from './upstream/src/string';

const schema = object().shape({
  first: string().when('second', { is: undefined, then: string().required() }),
  second: string().when('first', { is: undefined, then: string().required() }),
}, [['first', 'second']]);
const combined = schema.concat(object());
assert.equal(combined.isValidSync({ first: 'present' }), true);
