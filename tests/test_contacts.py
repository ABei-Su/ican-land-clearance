import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from record_contacts import contact_blocks, load_contact_entries
import tempfile
import json


class ContactTests(unittest.TestCase):
    def test_partial_and_restarted_recordings_are_merged_in_time_order(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            (root/'contacts.jsonl').write_text(json.dumps({'wall_time':2,'collisions':['bullet_a','target_a']})+'\n')
            (root/'contacts-live.jsonl').write_text(json.dumps({'wall_time':1,'collisions':['bullet_b','target_b']})+'\n')
            records=load_contact_entries(root)
            self.assertEqual([r['wall_time'] for r in records],[1,2])
            self.assertEqual(records[0]['source'],'contacts-live.jsonl')

    def test_nested_contacts_keep_only_bullets_and_no_partial_block(self):
        text='contact {\n collision1: "wheel"\n}\ncontact {\n collision1: "bullet_a::link::collision"\n position {\n x: 1\n }\n collision2: "target_wheel::link::leaf_1_collision"\n}\ncontact {\n collision1: "bullet_b"\n'
        blocks=list(contact_blocks(text.splitlines(True)))
        self.assertEqual(len(blocks),1)
        self.assertIn('leaf_1_collision',blocks[0])
        self.assertIn('x: 1',blocks[0])
