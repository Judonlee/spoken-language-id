import tensorflow as tf


def languid_rnn(features, training, params):
    # A sequence of spectrograms representing a sample audio, (batch_size, timesteps, bins)
    batch_size = tf.shape(features)[0]
    input_sgram = tf.reshape(features, [batch_size, -1, params.spectrogram_bins])
    normal_input = tf.subtract(tf.multiply(input_sgram, 2), 1)

    with tf.variable_scope("GRU1"):
        gru_cell = tf.contrib.rnn.GRUCell(num_units=params.gru_num_units)
        output_gru, final_state = tf.nn.dynamic_rnn(gru_cell, normal_input, dtype=tf.float32)

        if params.normalize:
            # Optional layer normalization
            output_gru = tf.contrib.layers.layer_norm(output_gru)

    with tf.variable_scope("GRU2"):
        gru_cell = tf.contrib.rnn.GRUCell(num_units=params.gru_num_units)
        output_gru, final_state = tf.nn.dynamic_rnn(gru_cell, output_gru, dtype=tf.float32)

        if params.normalize:
            # Optional layer normalization
            final_state = tf.contrib.layers.layer_norm(final_state)

        if params.dropout:
            # Optional dropout
            final_state = tf.layers.dropout(final_state, rate=params.dropout, training=training)

    # The prediction layer
    dense = tf.layers.dense(inputs=final_state, units=params.language_count)

    return dense


def model_fn(features, labels, mode, params):
    logits = languid_rnn(features, training=mode == tf.estimator.ModeKeys.TRAIN, params=params)

    # The prediction
    pred_classes = tf.argmax(logits, axis=-1)
    pred_probabilities = tf.nn.softmax(logits)
    predictions = {
        'class': pred_classes,
        'probs': pred_probabilities,
    }

    # If predicting, no need to define loss etc.
    if mode == tf.estimator.ModeKeys.PREDICT:
        return tf.estimator.EstimatorSpec(mode, predictions=predictions)

    onehot_labels = tf.one_hot(labels, depth=params.language_count)
    loss = tf.losses.softmax_cross_entropy(onehot_labels, logits)
    if params.regularize:
        # Add L2 regularization if configured
        l2_regularizer = tf.contrib.layers.l2_regularizer(params.regularize)
        loss += tf.contrib.layers.apply_regularization(
            l2_regularizer, tf.trainable_variables()
        )

    optimizer = tf.train.MomentumOptimizer(
        learning_rate=params.learning_rate,
        momentum=params.momentum
    ).minimize(loss, global_step=tf.train.get_global_step())

    # Evaluate the accuracy of the model
    accuracy, acc_op = tf.metrics.accuracy(labels=labels, predictions=pred_classes)

    if mode == tf.estimator.ModeKeys.TRAIN:
        tf.summary.scalar('train_loss', loss)
        tf.summary.scalar('train_accuracy', tf.reduce_mean(accuracy))

    return tf.estimator.EstimatorSpec(
        mode=mode,
        predictions=predictions,
        loss=loss,
        train_op=optimizer,
        eval_metric_ops={'accuracy': (accuracy, acc_op)}
    )
