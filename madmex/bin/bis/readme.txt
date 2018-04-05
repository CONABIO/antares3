BIS API readme.txt
  
  For streamlined processing see workflow.py
  For documentation, examples, dependencies and copyright see segment.py source code

Run from the Python interpreter:
  
  >>> import bis
  >>> help(bis.segment) # Review options and examples
  >>> bis.segment('bis/test/ag.bmp', t=[20, 50], tile=True)  # Segment and save output
  >>> bis.workflow('bis/test/ag.bmp', t=[20, 50], tile=True) # Segment and postprocess

Run from the command line:
  
  C:\bis> python segment.py --help
  C:\bis> python segment.py test\ag.bmp -t [20,50] --tile True # No spaces in args
  C:\bis> python workflow.py test\ag.bmp -t [20,50] --tile True
  
  C:\bis> python segment.py --test # Confirm tests run for each module


For end user license agreement, please see license_agreement.txt
Support and suggestions: support@BerkEnviro.com, +1-877-322-4670 (California)
