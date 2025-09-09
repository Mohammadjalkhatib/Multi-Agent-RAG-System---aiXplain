from aixplain.factories import PipelineFactory
p = PipelineFactory.get("68bc1d45def19d770c260355")
print("Dir:", [a for a in dir(p) if not a.startswith("_")])
print("Maybe inputs?:", getattr(p, "inputs", None))
print("Schema?:", getattr(p, "input_schema", None))
print("Meta?:", getattr(p, "metadata", None))
