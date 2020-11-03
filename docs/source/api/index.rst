#####################
Library API Reference
#####################

With the library API, you can run, schedule, and monitor notebook execution using Python code.

To use the library, just import it. These examples assume you import it as "run"::

  import sagemaker_run_notebook as run

To run a notebook immediately and wait for the result, use :meth:`invoke`, :meth:`wait_for_complete`, 
and :meth:`download_notebook`::

  job = run.invoke("powers.ipynb")
  run.wait_for_complete(job)
  run.download_notebook(job)

To schedule a notebook to run Sunday mornings at 3AM (UTC), use the :meth:`schedule` function::

  run.schedule("powers.ipynb", rule_name="powers", schedule="cron(0 3 ? * SUN *)")

To see the last two scheduled runs for a rule::

  runs = run.list_runs(n=2, rule="powers")
  runs

And to download the output notebooks::

  run.download_all(runs)

.. automodule:: sagemaker_run_notebook
    :members:
    :undoc-members:
    :show-inheritance:
    :autosummary: